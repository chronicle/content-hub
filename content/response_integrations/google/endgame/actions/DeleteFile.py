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
from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.EndgameManager import EndgameManager, EndgameNotFoundError
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from TIPCommon import extract_configuration_param, extract_action_param
import sys
import json


INTEGRATION_NAME = "Endgame"
SCRIPT_NAME = "Delete File"
INVESTIGATION_NAME = "Siemplify Delete File"
SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


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

    full_file_path = extract_action_param(
        siemplify,
        param_name="File Path",
        is_mandatory=True,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    successful_entities = []
    task_ids = {}
    missing_entities = []
    inactive_entities = []
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

                if not endpoint.is_active:
                    siemplify.LOGGER.info(
                        f"Endpoint {entity.identifier} is inactive. Skipping"
                    )
                    inactive_entities.append(entity.identifier)
                    continue

                if endpoint.sensors:
                    sensor_ids = [sensor.id for sensor in endpoint.sensors]

                    task_description_id = endgame_manager.get_task_id(
                        "deleteFileRequest", endpoint.core_os.lower()
                    )
                    task = endgame_manager.create_delete_file_task(
                        existing_path=full_file_path
                    )

                    task_bulk_id = endgame_manager.initialize_task(
                        task_id=task_description_id,
                        sensor_ids=sensor_ids,
                        task=task,
                        core_os=endpoint.core_os,
                    )

                    siemplify.LOGGER.info(
                        f"Successfully created task {task_bulk_id} for {entity.identifier}"
                    )

                    task_ids[entity.identifier] = task_bulk_id
                    successful_entities.append(entity.identifier)

            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            output_message += "Successfully initiated file deletion on the following entities:\n   {}".format(
                "\n   ".join([entity for entity in successful_entities])
            )

            if missing_entities:
                output_message += "\n\nThe following entities didn't match any endpoint and were skipped:\n   {}".format(
                    "\n   ".join([entity for entity in missing_entities])
                )

            if inactive_entities:
                output_message += "\n\nThe following endpoints are not active and were skipped:\n   {}".format(
                    "\n   ".join([entity for entity in inactive_entities])
                )

            if failed_entities:
                output_message += "\n\nError occurred while initiating file deletion on the following entities:\n   {}".format(
                    "\n   ".join([entity for entity in failed_entities])
                )

            output_message += "\n\nWaiting for tasks to complete."

            result_value = json.dumps(
                {
                    "task_ids": task_ids,
                    "successful_entities": successful_entities,
                    "missing_entities": missing_entities,
                    "inactive_entities": inactive_entities,
                    "failed_entities": failed_entities,
                }
            )

            status = EXECUTION_STATE_INPROGRESS

        else:
            # No sensor ids were found
            output_message = (
                "No suitable endpoints were found. Unable to initiate task."
            )
            result_value = "false"
            status = EXECUTION_STATE_FAILED

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

    siemplify.LOGGER.info("----------------- Async - Started -----------------")

    result_value = "false"
    output_message = ""
    error_entities = []
    failed_entities = []
    successful_entities = []
    status = EXECUTION_STATE_COMPLETED

    action_details = json.loads(siemplify.parameters["additional_data"])
    task_ids = action_details["task_ids"]
    missing_entities = action_details["missing_entities"]
    inactive_entities = action_details["inactive_entities"]
    init_failed_entities = action_details["failed_entities"]

    try:
        endgame_manager = EndgameManager(
            api_root, username=username, password=password, use_ssl=verify_ssl
        )

        # Check if tasks have all completed
        for bulk_task_id in list(task_ids.values()):
            try:
                if not endgame_manager.is_task_complete(bulk_task_id):
                    siemplify.LOGGER.info("Tasks have not completed yet. Waiting")
                    output_message = "Tasks have not completed yet. Waiting"
                    result_value = siemplify.parameters["additional_data"]
                    status = EXECUTION_STATE_INPROGRESS
                    siemplify.end(output_message, result_value, status)

            except Exception as e:
                siemplify.LOGGER.info(f"Failed to check status of task {bulk_task_id}")
                siemplify.LOGGER.exception(e)
                output_message = f"An error occurred while running action. Failed to check status of task {bulk_task_id}"
                status = EXECUTION_STATE_FAILED
                siemplify.end(output_message, "false", status)

        siemplify.LOGGER.info("All tasks have completed.")

        result_value = "true"
        status = EXECUTION_STATE_COMPLETED

        for entity_identifier, bulk_task_id in list(task_ids.items()):
            try:
                if endgame_manager.is_task_failed(bulk_task_id):
                    try:
                        collection_id = (
                            endgame_manager.get_collection_id_by_bulk_task_id(
                                bulk_task_id
                            )
                        )
                        collection = endgame_manager.get_collection_by_id(collection_id)

                        local_msg = collection.get("local_msg")
                        system_msg = collection.get("system_msg")

                        siemplify.LOGGER.error(
                            f"Delete file task failed on entity {entity_identifier}. Local message: {local_msg}. System message: {system_msg}"
                        )
                        failed_entities.append(
                            (entity_identifier, local_msg, system_msg)
                        )
                    except Exception as e:
                        error_entities.append(entity_identifier)
                        siemplify.LOGGER.error(
                            f"Failed to discover task failure reason for entity {entity_identifier}"
                        )
                        siemplify.LOGGER.exception(e)

                else:
                    siemplify.LOGGER.info(
                        f"File deletion task {bulk_task_id} of entity {entity_identifier} completed successfully."
                    )
                    successful_entities.append(entity_identifier)

            except Exception as e:
                error_entities.append(entity_identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity_identifier}"
                )
                siemplify.LOGGER.exception(e)

        output_message = (
            "Successfully deleted files from the following entities:\n   {}".format(
                "\n   ".join([entity for entity in successful_entities])
            )
        )

        if failed_entities:
            output_message += "\n\nFile deletion task has failed on the following entities:\n   {}".format(
                "\n   ".join(
                    [
                        f"{entity}: Local Message: {local_msg}, System Message: {system_msg}"
                        for (entity, local_msg, system_msg) in failed_entities
                    ]
                )
            )

        if missing_entities:
            output_message += "\n\nThe following entities didn't match any endpoint and were skipped:\n   {}".format(
                "\n   ".join([entity for entity in missing_entities])
            )

        if inactive_entities:
            output_message += "\n\nThe following endpoints are not active and were skipped:\n   {}".format(
                "\n   ".join([entity for entity in inactive_entities])
            )

        if init_failed_entities:
            output_message += "\n\nError occurred while initiating file deletion on the following entities:\n   {}".format(
                "\n   ".join([entity for entity in init_failed_entities])
            )

        if error_entities:
            output_message += "\n\nError occurred while running file delete task on the following entities:\n   {}".format(
                "\n   ".join([entity for entity in error_entities])
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

    siemplify.LOGGER.info("----------------- Async - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        async_action()
