# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import sys
import json

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler, unix_now, convert_dict_to_json_result_dict
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_TIMEDOUT,
)

from TIPCommon.extraction import extract_configuration_param, extract_action_param
from TIPCommon.transformation import string_to_multi_value

from crowd_strike_falcon.core.constants import (
    INTEGRATION_NAME,
    PRODUCT_NAME,
    CONTAIN_ENDPOINT_SCRIPT_NAME,
    API_ROOT_DEFAULT,
    CID_ERROR,
    DeviceStatusEnum,
    ENTITIES_MAPPER,
)
from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.exceptions import CrowdStrikeTimeoutError, InvalidCidError
from crowd_strike_falcon.core.utils import get_entity_original_identifier, is_action_approaching_timeout, validate_device_id


@output_handler
def main(is_first_run):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()

    siemplify.script_name = CONTAIN_ENDPOINT_SCRIPT_NAME
    mode = "Main" if is_first_run else "QueryState"

    siemplify.LOGGER.info(f"----------------- {mode} - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        default_value=API_ROOT_DEFAULT,
    )
    client_id = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API ID"
    )
    client_secret = extract_configuration_param(
        siemplify, provider_name=INTEGRATION_NAME, param_name="Client API Secret"
    )
    use_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=True,
        default_value=False,
    )
    integration_cid = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Customer ID",
        print_value=True
    )
    action_cid = extract_action_param(
        siemplify,
        param_name="Customer ID",
        print_value=True,
    )
    customer_id = action_cid or integration_cid

    fail_if_timeout = extract_action_param(
        siemplify, param_name="Fail If Timeout", input_type=bool, default_value=False
    )

    siemplify.LOGGER.info(f"----------------- {mode} - Started -----------------")
    status = EXECUTION_STATE_COMPLETED
    json_result = {}
    output_message = ""
    force_no_success = False
    result_value = {
        "pending": [],
        "failed": [],
        "ready": [],
        "skipped": [],
        "containment_pending_endpoints": [],
    }

    try:
        if is_first_run:
            # set pending entities
            result_value["pending"] = [
                [entity.entity_type, get_entity_original_identifier(entity)]
                for entity in (
                    entity
                    for entity in siemplify.target_entities
                    if entity.entity_type in ENTITIES_MAPPER
                )
            ]
            device_id_param = extract_action_param(
                siemplify,
                param_name="Device ID",
                print_value=True,
            )
            validate_device_id(device_id_param)
            device_ids = string_to_multi_value(device_id_param)
            for device_id in device_ids:
                result_value["pending"].append(["DEVICE_ID", device_id])
        else:
            result_value = json.loads(
                extract_action_param(siemplify=siemplify, param_name="additional_data")
            )

        manager = CrowdStrikeManager(
            api_root=api_root,
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            force_check_connectivity=True,
            customer_id=customer_id,
        )

        is_timeout_approached = False
        seen_devices = {}

        for entity_type, entity_identifier in result_value["pending"].copy():
            entity = [entity_type, entity_identifier]
            try:
                if entity_type == "DEVICE_ID":
                    devices = manager.get_devices(devices_ids=[entity_identifier])
                else:
                    request_filter = {
                        key: entity_identifier for key in ENTITIES_MAPPER[entity_type]
                    }
                    request_filter["cid"] = customer_id
                    devices = manager.search_devices(**request_filter)

                if is_action_approaching_timeout(
                    action_start_time, siemplify.execution_deadline_unix_time_ms
                ):
                    siemplify.LOGGER.info("Timeout was approached.")
                    is_timeout_approached = True
                    break

                if not devices:
                    siemplify.LOGGER.info(
                        f"No device found for entity {entity_identifier}. Skipping."
                    )
                    result_value["pending"].remove(entity)
                    # no data, add to failed entities
                    result_value["failed"].append(entity_identifier)
                    continue

                device = devices[0]

                if device.device_id in seen_devices:
                    siemplify.LOGGER.info(
                        f"Identifier '{entity_identifier}' maps to device ID '{device.device_id}', which is already "
                        f"associated with entity '{seen_devices[device.device_id]}'. Skipping duplication."
                    )
                    if entity in result_value["pending"]:
                        result_value["pending"].remove(entity)
                    continue

                seen_devices[device.device_id] = entity_identifier

                if is_first_run:
                    if device.match_status(DeviceStatusEnum.CONTAINED.value):
                        result_value["pending"].remove(entity)
                        siemplify.LOGGER.info(
                            f'Mark device: {entity_identifier} with stats "{device.status}" as skipped'
                        )
                        result_value["skipped"].append(entity)

                    # skip endpoints with status CONTAINMENT_PENDING and process only the rest statuses
                    elif not device.match_status(
                        DeviceStatusEnum.CONTAINMENT_PENDING.value
                    ):
                        siemplify.LOGGER.info(
                            f"Starts containing {entity_identifier}"
                        )
                        manager.contain_host_by_device_id(device.device_id)
                        siemplify.LOGGER.info(
                            f"Containment initiated successfully for {entity_identifier}"
                        )
                        result_value["containment_pending_endpoints"].append(
                            entity_identifier
                        )

                    elif (
                        entity_identifier
                        not in result_value["containment_pending_endpoints"]
                    ):
                        result_value["containment_pending_endpoints"].append(
                            entity_identifier
                        )
                else:
                    if device.match_status(DeviceStatusEnum.CONTAINED.value):
                        result_value["pending"].remove(entity)

                        if (
                            entity_identifier
                            in result_value["containment_pending_endpoints"]
                        ):
                            siemplify.LOGGER.info(
                                f'Mark device: {entity_identifier} with stats "{device.status}" as ready'
                            )
                            result_value["ready"].append(entity)
                            result_value["containment_pending_endpoints"].remove(
                                entity_identifier
                            )
                        else:
                            siemplify.LOGGER.info(
                                f'Mark device: {entity_identifier} with stats "{device.status}" as skipped'
                            )
                            result_value["skipped"].append(entity)

                    elif device.match_status(
                        DeviceStatusEnum.CONTAINMENT_PENDING.value
                    ):
                        siemplify.LOGGER.info(
                            f'Device: {entity_identifier} with stats "{device.status}" is still in progress'
                        )
                    else:
                        siemplify.LOGGER.info(
                            f'Containment for device: {entity_identifier} was aborted because the device status changed externally to "{device.status}".'
                        )
                        result_value["pending"].remove(entity)

                        if (
                            entity_identifier
                            in result_value["containment_pending_endpoints"]
                        ):
                            result_value["containment_pending_endpoints"].remove(
                                entity_identifier
                            )

                        result_value.setdefault("aborted", []).append(entity)

            except Exception as e:
                if CID_ERROR in str(e).lower():
                    raise InvalidCidError(
                        "Incorrect Customer ID specified."
                    ) from e

                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)
                if entity in result_value["pending"]:
                    result_value["pending"].remove(entity)

                result_value["failed"].append(entity_identifier)

        pending_endpoints = [identifier for _, identifier in result_value["pending"]]

        timeout_message = (
            "The following endpoints initiated containment, but were not able to finish it "
            f'during action execution: {", ".join(pending_endpoints)}\n'
        )

        if result_value["pending"]:
            if is_timeout_approached:
                if result_value["containment_pending_endpoints"]:
                    output_message = timeout_message
                    force_no_success = True
                    if fail_if_timeout:
                        raise CrowdStrikeTimeoutError(output_message)
                else:
                    siemplify.LOGGER.error(
                        "Action was not able to finish iteration because of small value of timeout."
                    )
                    status = EXECUTION_STATE_TIMEDOUT
                    result_value = False
            else:
                result_value = json.dumps(result_value)
                status = EXECUTION_STATE_INPROGRESS
                output_message = (
                    f"Waiting for containment to finish for the following endpoints: "
                    f'{", ".join(pending_endpoints)}'
                )

        elif result_value["ready"] or result_value["skipped"]:
            for entity_type, identifier in (
                result_value["ready"] + result_value["skipped"]
            ):
                # start fetching containment
                if entity_type == "DEVICE_ID":
                    devices = manager.get_devices(devices_ids=[identifier])
                else:
                    request_filter = {
                        key: identifier for key in ENTITIES_MAPPER[entity_type]
                    }
                    request_filter["cid"] = customer_id
                    devices = manager.search_devices(**request_filter)
                if not devices:
                    # device was removed during the iterations
                    result_value["failed"].append(identifier)
                    continue

                if is_action_approaching_timeout(
                    action_start_time, siemplify.execution_deadline_unix_time_ms
                ):
                    siemplify.LOGGER.info("Timeout was approached.")
                    result_value["failed"].append(identifier)

                    if fail_if_timeout:
                        raise CrowdStrikeTimeoutError(timeout_message)

                json_result[identifier] = devices[0].to_json()

        result = result_value
        if status != EXECUTION_STATE_INPROGRESS and isinstance(result, dict):
            if result_value["ready"]:
                output_message += (
                    f"Successfully contained the following endpoints in {PRODUCT_NAME}: "
                    f'{", ".join([identifier for _, identifier in result_value["ready"]])}\n'
                )
                result_value = True

            if result["skipped"]:
                output_message += (
                    f"The following endpoints were already contained {PRODUCT_NAME}: "
                    f'{", ".join([identifier for _, identifier in result["skipped"]])}\n'
                )
                result_value = True

            if result.get("aborted"):
                output_message += (
                    f"Containment was aborted for the following endpoints due to external state change in {PRODUCT_NAME}: "
                    f'{", ".join([identifier for _, identifier in result["aborted"]])}\n'
                )

            if result["failed"]:
                output_message += (
                    f"The following endpoints were not found in {PRODUCT_NAME}: "
                    f'{", ".join(result["failed"])}\n'
                )
            if json_result:
                result_value = True
                siemplify.result.add_result_json(
                    convert_dict_to_json_result_dict(json_result)
                )

            elif not (result["skipped"] or result_value["ready"] or result["pending"]):
                if not result.get("aborted"):
                    output_message = (
                        f"None of the provided endpoints were found in {PRODUCT_NAME}."
                    )
                result_value = False

        if force_no_success:
            result_value = False
    except Exception as e:
        output_message = (
            f"Error executing action '{CONTAIN_ENDPOINT_SCRIPT_NAME}'. Reason: {e}"
        )
        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
