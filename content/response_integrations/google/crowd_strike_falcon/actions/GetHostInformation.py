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
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon.extraction import extract_action_param, extract_configuration_param
from TIPCommon.transformation import string_to_multi_value

from crowd_strike_falcon.core.CrowdStrikeManager import CrowdStrikeManager
from crowd_strike_falcon.core.constants import (
    API_ROOT_DEFAULT,
    CID_ERROR,
    DEFAULT_DEVICES_LIMIT,
    ENTITIES_MAPPER,
    GET_HOST_INFORMATION_SCRIPT_NAME,
    INTEGRATION_NAME,
    PRODUCT_NAME,
)
from crowd_strike_falcon.core.utils import (
    MockEntity,
    get_entity_original_identifier,
    validate_device_id,
)


EXCLUDE_KEYS_DEFAULT = ["policies", "device_policies"]


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = GET_HOST_INFORMATION_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

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
    )

    create_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        default_value=True,
        print_value=True,
        input_type=bool,
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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    successful_entities, failed_entities, json_results = [], [], {}
    login_histories, online_states = {}, {}
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in ENTITIES_MAPPER
    ]
    device_id_param = extract_action_param(
        siemplify,
        param_name="Device ID",
        print_value=True,
    )
    device_ids = string_to_multi_value(device_id_param)
    for device_id in device_ids:
        suitable_entities.append(MockEntity(device_id, "DEVICE_ID"))

    try:
        validate_device_id(device_id_param)
        manager = CrowdStrikeManager(
            client_id=client_id,
            client_secret=client_secret,
            use_ssl=use_ssl,
            api_root=api_root,
            customer_id=customer_id,
        )
        seen_devices = {}
        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            if entity.entity_type == "DEVICE_ID":
                devices = manager.get_devices(devices_ids=[entity_identifier])
            else:
                request_filter = {
                    key: entity_identifier
                    for key in ENTITIES_MAPPER[entity.entity_type]
                }
                request_filter["cid"] = customer_id

                devices = manager.search_devices(
                    include_hidden_hosts=True,
                    limit=DEFAULT_DEVICES_LIMIT,
                    **request_filter,
                )

            if not devices:
                failed_entities.append(entity_identifier)
                continue

            unseen_devices = []
            for device in devices:
                if device.device_id in seen_devices:
                    siemplify.LOGGER.info(
                        f"Identifier '{entity_identifier}' maps to device ID '{device.device_id}', which is already "
                        f"associated with entity '{seen_devices[device.device_id]}'. Skipping duplication."
                    )
                else:
                    unseen_devices.append(device)

            if not unseen_devices:
                continue

            devices = unseen_devices
            for device in devices:
                seen_devices[device.device_id] = entity_identifier

            try:
                login_histories = {
                    item.device_id: item.recent_logins
                    for item in manager.get_devices_login_histories(
                        ids=[device.device_id for device in devices], cid=customer_id
                    )
                }

            except Exception:
                siemplify.LOGGER.error(
                    f"An error occurred on getting login history for entity {entity.identifier}"
                )

            try:
                online_states = {
                    item.device_id: item.state
                    for item in manager.get_devices_online_states(
                        [device.device_id for device in devices]
                    )
                }
            except Exception:
                siemplify.LOGGER.error(
                    f"An error occurred on getting online state for entity {entity.identifier}"
                )

            for index, device in enumerate(devices):
                device_data = device.to_enrichment_data(
                    exclude_keys=EXCLUDE_KEYS_DEFAULT,
                    additional_prefix=index if len(devices) != 1 else None,
                )
                entity.additional_properties.update(device_data)

                if create_insight and entity.entity_type != "DEVICE_ID":
                    siemplify.add_entity_insight(
                        entity, device.to_insight(entity_type=entity.entity_type)
                    )

            entity.is_enriched = True
            successful_entities.append(entity)

            json_results[entity_identifier] = [
                {
                    **device.to_json(),
                    "recent_logins": login_histories.get(device.device_id, []),
                    "online_status": online_states.get(device.device_id, ""),
                }
                for device in devices
            ]

        if successful_entities:
            output_message = (
                f"Successfully enriched the following entities using {PRODUCT_NAME}: "
                f'{", ".join([get_entity_original_identifier(entity) for entity in successful_entities])}\n'
            )
            real_successful_entities = [entity for entity in successful_entities if entity.entity_type != "DEVICE_ID"]
            if real_successful_entities:
                siemplify.update_entities(real_successful_entities)

            if failed_entities:
                output_message += (
                    f"Action wasn't able to enrich the following entities using {PRODUCT_NAME}: "
                    f'{", ".join(failed_entities)}\n'
                )
        else:
            result_value = False
            output_message = "No entities were enriched."

        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

    except Exception as e:
        error_message = f"Error executing action {GET_HOST_INFORMATION_SCRIPT_NAME}."
        output_message = f"{error_message} Reason: {e}"
        if CID_ERROR in str(e).lower():
            output_message = f"{error_message} Reason: Incorrect Customer ID specified."

        status = EXECUTION_STATE_FAILED
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
