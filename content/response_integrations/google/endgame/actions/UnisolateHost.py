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
from soar_sdk.SiemplifyUtils import unix_now, convert_unixtime_to_datetime, output_handler
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from ..core.EndgameManager import EndgameManager, EndgameNotFoundError, RELEASE_REQUESTED
from TIPCommon import extract_configuration_param, extract_action_param

INTEGRATION_NAME = "Endgame"
SCRIPT_NAME = "Get Endpoints"
SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
WINDOWS_OS = "windows"
MAC_OS = "macos"
SUPPORTED_OS = [WINDOWS_OS, MAC_OS]
TASK_NAME = "hostIsolationReleaseRequest"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    # INIT INTEGRATION CONFIGURATION:
    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="API Root",
        is_mandatory=True,
        input_type=str,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Username",
        is_mandatory=True,
        input_type=str,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Password",
        is_mandatory=True,
        input_type=str,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    is_insight = extract_action_param(
        siemplify,
        param_name="Create Insight",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    missing_entities = []
    no_sensors_entities = []
    failed_entities = []
    error_entities = []
    output_message = ""
    result_value = "true"

    try:
        endgame_manager = EndgameManager(api_root, username, password, verify_ssl)

        for entity in siemplify.target_entities:
            if unix_now() >= siemplify.execution_deadline_unix_time_ms:
                siemplify.LOGGER.error(
                    f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
                )
                status = EXECUTION_STATE_TIMEDOUT
                break

            try:
                if entity.entity_type not in SUPPORTED_ENTITIES:
                    siemplify.LOGGER.info(
                        f"Entity {entity.identifier} is of unsupported type. Skipping."
                    )
                    continue

                siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
                matching_endpoints = []

                if entity.entity_type == EntityTypes.HOSTNAME:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching endpoint for hostname {entity.identifier}"
                        )
                        matching_endpoints = endgame_manager.get_endpoint_by_hostname(
                            entity.identifier
                        )
                    except EndgameNotFoundError as e:
                        # Endpoint was not found in Endgame - skip entity
                        missing_entities.append(entity)
                        siemplify.LOGGER.info(str(e))
                        siemplify.LOGGER.info(f"Skipping entity {entity.identifier}")
                        continue

                if entity.entity_type == EntityTypes.ADDRESS:
                    try:
                        siemplify.LOGGER.info(
                            f"Fetching endpoint for address {entity.identifier}"
                        )
                        matching_endpoints = endgame_manager.get_endpoint_by_ip(
                            entity.identifier
                        )
                    except EndgameNotFoundError as e:
                        # Endpoint was not found in Endgame - skip entity
                        missing_entities.append(entity)
                        siemplify.LOGGER.info(str(e))
                        siemplify.LOGGER.info(f"Skipping entity {entity.identifier}")
                        continue

                if len(matching_endpoints) > 1:
                    siemplify.LOGGER.info(
                        f"Multiple endpoints matching entity {entity.identifier} were found. First will be used."
                    )

                # Take the first matching endpoint
                endpoint = matching_endpoints[0]

                if endpoint.core_os.lower() not in SUPPORTED_OS:
                    siemplify.LOGGER.info(f"Endpoint OS is not supported. Skipping.")
                    continue

                task_id = endgame_manager.get_task_id(
                    TASK_NAME, endpoint.core_os.lower()
                )
                sensor_ids = (
                    [sensor.id for sensor in endpoint.sensors]
                    if endpoint.sensors
                    else []
                )

                if not sensor_ids:
                    siemplify.LOGGER.info("No sensors found for the endpoint. Skipping")
                    no_sensors_entities.append(entity)
                    continue

                endgame_manager.initialize_isolation_task(
                    task_id, sensor_ids, isolate=False
                )

                if (
                    endgame_manager.get_endpoint_by_id(
                        endpoint.id
                    ).isolation_request_status
                    == RELEASE_REQUESTED
                ):
                    siemplify.LOGGER.info(
                        f"Successfully initiated release of {entity.identifier} endpoint with Endgame"
                    )
                    successful_entities.append(entity)

                    if is_insight:
                        siemplify.add_entity_insight(
                            entity,
                            "Host release was initiated using Endgame",
                            triggered_by=INTEGRATION_NAME,
                        )

                else:
                    siemplify.LOGGER.info(
                        f"Failed to release isolation of {entity.identifier}."
                    )
                    failed_entities.append(entity)

            except Exception as e:
                error_entities.append(entity)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += "Successfully initiated release of the following entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in successful_entities])
            )
        else:
            output_message += "No entities were released."

        if missing_entities:
            output_message += "The following entities didn't match an any endpoint and were skipped:\n   {}".format(
                "\n   ".join([entity.identifier for entity in missing_entities])
            )

        if no_sensors_entities:
            output_message += "No sensors were found for the following entities and therefore were skipped:\n   {}".format(
                "\n   ".join([entity.identifier for entity in no_sensors_entities])
            )

        if failed_entities:
            output_message += (
                "Failed to initiate release of the following entities:\n   {}".format(
                    "\n   ".join([entity.identifier for entity in failed_entities])
                )
            )

        if error_entities:
            output_message += "Error occurred while initiating release of the following entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in error_entities])
            )

    except Exception as e:
        siemplify.LOGGER.error(f"Action didn't complete due to error: {e}")
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Action didn't complete due to error: {e}"

    finally:
        try:
            endgame_manager.logout()
        except Exception as e:
            siemplify.LOGGER.error(f"Logging out failed. Error: {e}")
            siemplify.LOGGER.exception(e)

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
