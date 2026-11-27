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
from soar_sdk.SiemplifyUtils import output_handler, convert_dict_to_json_result_dict
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.EndgameManager import EndgameManager, EndgameNotFoundError
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from TIPCommon import extract_configuration_param, extract_action_param, construct_csv
import sys
import json


INTEGRATION_NAME = "Endgame"
SCRIPT_NAME = "Drivers Survey"
INVESTIGATION_NAME = "Siemplify Drivers Survey"
SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]
SUPPORTED_OSES = ["windows"]


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

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    successful_entities = []
    investigation_ids = {}
    not_supported_entities = []
    missing_entities = []
    failed_entities = []
    status = EXECUTION_STATE_COMPLETED
    result_value = "false"
    output_message = ""

    try:
        endgame_manager = EndgameManager(
            api_root, username=username, password=password, use_ssl=verify_ssl
        )

        for entity in siemplify.target_entities:
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
                        missing_entities.append(entity.identifier)
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
                        missing_entities.append(entity.identifier)
                        siemplify.LOGGER.info(str(e))
                        siemplify.LOGGER.info(f"Skipping entity {entity.identifier}")
                        continue

                if len(matching_endpoints) > 1:
                    siemplify.LOGGER.info(
                        f"Multiple endpoints matching entity {entity.identifier} were found. First will be used."
                    )

                # Take the first matching endpoint
                endpoint = matching_endpoints[0]

                if endpoint.core_os.lower() not in SUPPORTED_OSES:
                    siemplify.LOGGER.info(
                        f"Endpoint {entity.identifier} OS is not supported for this action. Skipping"
                    )
                    not_supported_entities.append(entity.identifier)
                    continue

                if endpoint.sensors:
                    sensor_ids = [sensor.id for sensor in endpoint.sensors]

                    task_description_id = endgame_manager.get_task_id(
                        "kernelModulesSurveyRequest", endpoint.core_os
                    )

                    investigation_id = endgame_manager.create_investigation(
                        investigation_name=INVESTIGATION_NAME,
                        assign_user=username,
                        sensor_ids=sensor_ids,
                        tasks={task_description_id: {}},
                        core_os=endpoint.core_os.lower(),
                    )

                    siemplify.LOGGER.info(
                        f"Successfully created investigation {investigation_id} for {entity.identifier}"
                    )

                    investigation_ids[entity.identifier] = investigation_id
                    successful_entities.append(entity.identifier)

            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += "Successfully initiated drivers survey on the following entities:\n   {}".format(
                "\n   ".join([entity for entity in successful_entities])
            )

            status = EXECUTION_STATE_INPROGRESS

        else:
            # No sensor ids were found
            output_message = (
                "No suitable endpoints were found. Unable to initiate survey."
            )
            result_value = "false"
            status = EXECUTION_STATE_FAILED

        if missing_entities:
            output_message += "\n\nThe following entities didn't match any endpoint and were skipped:\n   {}".format(
                "\n   ".join([entity for entity in missing_entities])
            )

        if not_supported_entities:
            output_message += "\n\nThe following entities run an unsupported OS and were skipped:\n   {}".format(
                "\n   ".join([entity for entity in not_supported_entities])
            )

        if failed_entities:
            output_message += "\n\nError occurred while initiating drivers survey on the following entities:\n   {}".format(
                "\n   ".join([entity for entity in failed_entities])
            )

        if successful_entities:
            output_message += "\n\nWaiting for investigations to complete."

        result_value = json.dumps(
            {
                "investigation_ids": investigation_ids,
                "successful_entities": successful_entities,
                "missing_entities": missing_entities,
                "not_supported_entities": not_supported_entities,
                "failed_entities": failed_entities,
            }
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


def async_action():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"

    siemplify.LOGGER.info("================= Async - Param Init =================")

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

    results_limit = extract_action_param(
        siemplify,
        param_name="Max Items to Return",
        is_mandatory=False,
        input_type=int,
        print_value=True,
        default_value=None,
    )

    siemplify.LOGGER.info("----------------- Async - Started -----------------")

    result_value = "false"
    output_message = ""
    error_entities = []
    failed_entities = []
    successful_entities = []
    json_results = {}
    status = EXECUTION_STATE_COMPLETED

    action_details = json.loads(siemplify.parameters["additional_data"])
    investigation_ids = action_details["investigation_ids"]
    missing_entities = action_details["missing_entities"]
    not_supported_entities = action_details["not_supported_entities"]
    init_failed_entities = action_details["failed_entities"]

    try:
        endgame_manager = EndgameManager(
            api_root, username=username, password=password, use_ssl=verify_ssl
        )

        # Check if tasks have all completed
        for investigation_id in list(investigation_ids.values()):
            try:
                if not endgame_manager.is_investigation_complete(investigation_id):
                    siemplify.LOGGER.info(
                        "Investigations have not completed yet. Waiting"
                    )
                    output_message = "Investigations have not completed yet. Waiting"
                    result_value = siemplify.parameters["additional_data"]
                    status = EXECUTION_STATE_INPROGRESS
                    siemplify.end(output_message, result_value, status)

            except Exception as e:
                siemplify.LOGGER.info(
                    f"Failed to check status of investigation {investigation_id}"
                )
                siemplify.LOGGER.exception(e)
                output_message = f"An error occurred while running action. Failed to check status of investigation {investigation_id}"
                status = EXECUTION_STATE_FAILED
                siemplify.end(output_message, "false", status)

        siemplify.LOGGER.info("All investigations have completed.")

        result_value = "true"
        status = EXECUTION_STATE_COMPLETED

        for entity_identifier, investigation_id in list(investigation_ids.items()):
            try:
                results = []
                siemplify.LOGGER.info(
                    f"Collecting drivers information for {entity_identifier}"
                )
                # Collect the results of the investigation
                investigation_results = endgame_manager.retrieve_investigation_results(
                    investigation_id, scope="kernel_modules", limit=results_limit
                )

                for task_id, investigation_result in list(
                    investigation_results.items()
                ):
                    for result in investigation_result.get("Results", []):
                        results.append(result)

                json_results[entity_identifier] = results

                if results:
                    # Add table for each entity
                    siemplify.result.add_data_table(
                        f"Information about drivers from {entity_identifier}",
                        construct_csv([result_to_csv(result) for result in results]),
                    )
                successful_entities.append(entity_identifier)

            except Exception as e:
                error_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message = "Successfully completed drivers survey on the following entities:\n   {}".format(
                "\n   ".join([entity for entity in successful_entities])
            )

        else:
            output_message = "Drivers survey didn't run on any entities."
            result_value = "false"

        if failed_entities:
            output_message += "\n\nDrivers survey has failed on the following entities:\n   {}".format(
                "\n   ".join([entity for entity in failed_entities])
            )

        if missing_entities:
            output_message += "\n\nThe following entities didn't match any endpoint and were skipped:\n   {}".format(
                "\n   ".join([entity for entity in missing_entities])
            )

        if not_supported_entities:
            output_message += "\n\nThe following entities run an unsupported OS and were skipped:\n   {}".format(
                "\n   ".join([entity for entity in not_supported_entities])
            )

        if init_failed_entities:
            output_message += "\n\nError occurred while initiating drivers survey on the following entities:\n   {}".format(
                "\n   ".join([entity for entity in init_failed_entities])
            )

        if error_entities:
            output_message += "\n\nError occurred while running drivers survey on the following entities:\n   {}".format(
                "\n   ".join([entity for entity in error_entities])
            )

        siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

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

    siemplify.LOGGER.info("----------------- Async - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


def result_to_csv(result):
    # TODO: Create a datamodel for this type of result and move this method there
    return {
        "Name": result.get("driver_basename"),
        "File Path": result.get("driver_filename"),
        "Description": result.get("driver_description"),
        "Date Modified": result.get("date_modified"),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        async_action()
