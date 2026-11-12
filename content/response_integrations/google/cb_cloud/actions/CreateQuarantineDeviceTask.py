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
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import (
    unix_now,
    convert_unixtime_to_datetime,
    output_handler,
    convert_dict_to_json_result_dict,
)
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.CBCloudManager import CBCloudManager
from TIPCommon.extraction import extract_configuration_param
from ..core.constants import (
    INTEGRATION_NAME,
    QUARANTINE_DEVICE_SCRIPT_NAME,
    PROVIDER_NAME,
    NEW_LINE,
)
from ..core.utils import get_entity_original_identifier

SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
ENTITIES_MAPPER = {
    EntityTypes.ADDRESS: "query",
    EntityTypes.HOSTNAME: "starts_with_name",
}
DEFAULT_LIMIT = 3


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = QUARANTINE_DEVICE_SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
    )
    org_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Organization Key",
        is_mandatory=True,
    )
    api_id = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API ID",
        is_mandatory=True,
    )
    api_secret_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Secret Key",
        is_mandatory=True,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    result_value = True
    status = EXECUTION_STATE_COMPLETED
    (
        successful_entities,
        missing_entities,
        multimatch_entities,
        failed_entities,
        json_results,
    ) = ([], [], [], [], {})
    output_message = ""
    suitable_entities = [
        entity
        for entity in siemplify.target_entities
        if entity.entity_type in SUPPORTED_ENTITIES
    ]

    try:
        manager = CBCloudManager(
            api_root=api_root,
            org_key=org_key,
            api_id=api_id,
            api_secret_key=api_secret_key,
            verify_ssl=verify_ssl,
            force_check_connectivity=True,
        )

        for entity in suitable_entities:
            entity_identifier = get_entity_original_identifier(entity)
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline "
                    f"({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) "
                    f"has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                siemplify.LOGGER.info(f"Started processing entity: {entity_identifier}")
                siemplify.LOGGER.info(
                    f"Fetching device info for entity {entity_identifier}"
                )

                params = {
                    ENTITIES_MAPPER[entity.entity_type]: entity_identifier,
                    "limit": DEFAULT_LIMIT,
                }

                devices = manager.search_devices(**params)

                if not devices:
                    # Device was not found in CB Cloud - skip entity
                    missing_entities.append(entity_identifier)
                    json_results[entity_identifier] = {"status": "failure"}
                    siemplify.LOGGER.info(
                        f"No devices found for entity {entity_identifier}. Skipping."
                    )
                    continue

                if len(devices) > 1:
                    multimatch_entities.append(entity_identifier)
                    siemplify.LOGGER.info(
                        f"Multiple matches found for entity {entity_identifier}, taking first match for enrichment."
                    )

                device = devices[-1]

                siemplify.LOGGER.info(
                    f"Creating enable quarantine device task for device: {device.id}, entity:{entity_identifier}."
                )
                manager.create_quarantine_task(device.id)

                successful_entities.append(entity_identifier)
                json_results[entity_identifier] = {"status": "done"}
                siemplify.LOGGER.info(f"Finished processing entity {entity_identifier}")

            except Exception as e:
                failed_entities.append(entity_identifier)
                json_results[entity_identifier] = {"status": "failure"}
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += (
                f"Successfully created a quarantine device task for the following entities:\n "
                f"{NEW_LINE.join(successful_entities)} \n"
            )

            if failed_entities:
                output_message += (
                    f"Failed to create quarantine device tasks for the following entities:\n "
                    f"{NEW_LINE.join(failed_entities)} \n"
                )
        else:
            output_message += "No tasks were created. \n"
            result_value = False

        if multimatch_entities:
            output_message += (
                f"Multiple matches were found in {PROVIDER_NAME}, taking first match for the following "
                f"entities:\n   {NEW_LINE.join(multimatch_entities)}\n"
            )

        if missing_entities:
            output_message += (
                f"Action was not able to find matching {PROVIDER_NAME} devices for the following "
                f"entities:\n {NEW_LINE.join(missing_entities)} \n"
            )

        if json_results:
            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

    except Exception as e:
        output_message = (
            f"Error executing action {QUARANTINE_DEVICE_SCRIPT_NAME}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  is_success: {result_value}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
