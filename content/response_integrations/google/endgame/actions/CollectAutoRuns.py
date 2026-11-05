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
import base64
import json


INTEGRATION_NAME = "Endgame"
SCRIPT_NAME = "Collect Autoruns"
INVESTIGATION_NAME = "Siemplify AutoRun Collection"
WINDOWS_OS = "windows"
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

    category_all = extract_action_param(
        siemplify,
        param_name='Category "All"',
        is_mandatory=False,
        input_type=bool,
        default_value=True,
        print_value=True,
    )
    category_network_provider = extract_action_param(
        siemplify,
        param_name='Category "Network Provider"',
        is_mandatory=False,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    category_office = extract_action_param(
        siemplify,
        param_name='Category "Office"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_driver = extract_action_param(
        siemplify,
        param_name='Category "Driver"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_app_init = extract_action_param(
        siemplify,
        param_name='Category "App Init"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_winlogon = extract_action_param(
        siemplify,
        param_name='Category "Winlogon"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_print_monitor = extract_action_param(
        siemplify,
        param_name='Category "Print Monitor"',
        is_mandatory=False,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    category_ease_of_access = extract_action_param(
        siemplify,
        param_name='Category "Ease of Access"',
        is_mandatory=False,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    category_wmi = extract_action_param(
        siemplify,
        param_name='Category "WMI"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_lsa_provider = extract_action_param(
        siemplify,
        param_name='Category "LSA Provider"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_service = extract_action_param(
        siemplify,
        param_name='Category "Service"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_bits = extract_action_param(
        siemplify,
        param_name='Category "Bits"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_known_dll = extract_action_param(
        siemplify,
        param_name='Category "Known dll"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_print_provider = extract_action_param(
        siemplify,
        param_name='Category "Print Provider"',
        is_mandatory=False,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    category_image_hijack = extract_action_param(
        siemplify,
        param_name='Category "Image Hijack"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_startup_folder = extract_action_param(
        siemplify,
        param_name='Category "Startup Folder"',
        is_mandatory=False,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    category_internet_explorer = extract_action_param(
        siemplify,
        param_name='Category "Internet Explorer"',
        is_mandatory=False,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    category_codec = extract_action_param(
        siemplify,
        param_name='Category "Codec"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_logon = extract_action_param(
        siemplify,
        param_name='Category "Logon"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_search_order_hijack = extract_action_param(
        siemplify,
        param_name='Category "Search Order Hijack"',
        is_mandatory=False,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    category_winsock_provider = extract_action_param(
        siemplify,
        param_name='Category "Winsock Provider"',
        is_mandatory=False,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    category_boot_execute = extract_action_param(
        siemplify,
        param_name='Category "Boot Execute"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_phantom_dll = extract_action_param(
        siemplify,
        param_name='Category "Phantom dll"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_com_hijack = extract_action_param(
        siemplify,
        param_name='Category "Com Hijack"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_explorer = extract_action_param(
        siemplify,
        param_name='Category "Explorer"',
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    category_scheduled_task = extract_action_param(
        siemplify,
        param_name='Category "Scheduled Task"',
        is_mandatory=False,
        default_value=False,
        input_type=bool,
        print_value=True,
    )
    include_all_metadata = extract_action_param(
        siemplify,
        param_name="Include All Metadata",
        is_mandatory=False,
        input_type=bool,
        default_value=True,
        print_value=True,
    )
    include_malware_classification_metadata = extract_action_param(
        siemplify,
        param_name="Include Malware Classification Metadata",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    include_authenticode_metadata = extract_action_param(
        siemplify,
        param_name="Include Authenticode Metadata",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    include_md5_hash = extract_action_param(
        siemplify,
        param_name="Include MD5 Hash",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    include_sha1_hash = extract_action_param(
        siemplify,
        param_name="Include SHA-1 Hash",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )
    include_sha256_hash = extract_action_param(
        siemplify,
        param_name="Include SHA-256 Hash",
        is_mandatory=False,
        input_type=bool,
        default_value=False,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    sensor_ids = []
    successful_entities = []
    machine_ids = {}
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

                if endpoint.core_os.lower() != WINDOWS_OS:
                    siemplify.LOGGER.info(
                        f"Endpoint {entity.identifier} OS in not supported. Skipping."
                    )
                    continue

                if endpoint.sensors:
                    successful_entities.append(entity.identifier)
                    sensor_ids.extend([sensor.id for sensor in endpoint.sensors])
                    machine_ids[endpoint.machine_id] = entity.identifier

            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            siemplify.LOGGER.info(
                "Initiating Autorun collection task on the following entities: {}".format(
                    "\n   ".join([entity for entity in successful_entities])
                )
            )

            task_id = endgame_manager.get_task_id(
                "collectAutoRunsRequest", endpoint.core_os.lower()
            )
            task = endgame_manager.create_autorun_collection_task(
                category_all=category_all,
                category_network_provider=category_network_provider,
                category_office=category_office,
                category_driver=category_driver,
                category_app_init=category_app_init,
                category_winlogon=category_winlogon,
                category_print_monitor=category_print_monitor,
                category_ease_of_access=category_ease_of_access,
                category_wmi=category_wmi,
                category_lsa_provider=category_lsa_provider,
                category_service=category_service,
                category_bits=category_bits,
                category_known_dll=category_known_dll,
                category_print_provider=category_print_provider,
                category_image_hijack=category_image_hijack,
                category_startup_folder=category_startup_folder,
                category_internet_explorer=category_internet_explorer,
                category_codec=category_codec,
                category_logon=category_logon,
                category_search_order_hijack=category_search_order_hijack,
                category_winsock_provider=category_winsock_provider,
                category_boot_execute=category_boot_execute,
                category_phantom_dll=category_phantom_dll,
                category_com_hijack=category_com_hijack,
                category_explorer=category_explorer,
                category_scheduled_task=category_scheduled_task,
                include_all_metadata=include_all_metadata,
                include_malware_classification_metadata=include_malware_classification_metadata,
                include_authenticode_metadata=include_authenticode_metadata,
                include_md5_hash=include_md5_hash,
                include_sha1_hash=include_sha1_hash,
                include_sha256_hash=include_sha256_hash,
            )

            # By default, the investigation is assigned to the login user
            investigation_id = endgame_manager.create_investigation(
                investigation_name=INVESTIGATION_NAME,
                assign_user=username,
                sensor_ids=sensor_ids,
                tasks={task_id: task},
                core_os=WINDOWS_OS,
            )

            siemplify.LOGGER.info(
                f"Successfully created investigation {investigation_id}"
            )

            if successful_entities:
                output_message += "Successfully initiated Autoruns collection on the following entities:\n   {}".format(
                    "\n   ".join([entity for entity in successful_entities])
                )

            if missing_entities:
                output_message += "\n\nThe following entities didn't match an any endpoint and were skipped:\n   {}".format(
                    "\n   ".join([entity for entity in missing_entities])
                )

            if failed_entities:
                output_message += "\n\nError occurred while initiating Autoruns collection on the following entities:\n   {}".format(
                    "\n   ".join([entity for entity in failed_entities])
                )

            output_message += f"\n\nInvestigation ID: {investigation_id}. Waiting for investigation to complete."

            result_value = json.dumps(
                {
                    "machine_ids": machine_ids,
                    "investigation_id": investigation_id,
                    "successful_entities": successful_entities,
                    "missing_entities": missing_entities,
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
    results_limit = extract_action_param(
        siemplify,
        param_name="Max Items to Return",
        is_mandatory=False,
        input_type=int,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Async - Started -----------------")

    result_value = "false"
    output_message = ""
    json_results = {}
    results = []
    status = EXECUTION_STATE_COMPLETED

    action_details = json.loads(siemplify.parameters["additional_data"])
    investigation_id = action_details["investigation_id"]
    successful_entities = action_details["successful_entities"]
    missing_entities = action_details["missing_entities"]
    failed_entities = action_details["failed_entities"]
    machine_ids = action_details["machine_ids"]

    try:
        endgame_manager = EndgameManager(
            api_root, username=username, password=password, use_ssl=verify_ssl
        )

        # Check if investigation completed
        if endgame_manager.is_investigation_complete(investigation_id):
            siemplify.LOGGER.info(
                f"Investigation {investigation_id} has completed. Collecting results."
            )

            # Collect the results of the investigation
            investigation_results = endgame_manager.retrieve_investigation_results(
                investigation_id, limit=results_limit
            )

            for task_id, investigation_result in list(investigation_results.items()):
                for result in investigation_result.get("Results", []):
                    results.append(result)

            result_value = "true"
            status = EXECUTION_STATE_COMPLETED

            results_by_entity = match_results_to_entity(machine_ids, results)

            for entity_identifier in successful_entities:
                entity_autoruns = results_by_entity.get(entity_identifier, [])
                json_results[entity_identifier] = entity_autoruns

                if entity_autoruns:
                    # Add table for each entity
                    siemplify.result.add_data_table(
                        f"Collected autoruns from {entity_identifier}",
                        construct_csv(
                            [result_to_csv(result) for result in entity_autoruns]
                        ),
                    )

            siemplify.result.add_attachment(
                "Collected Autoruns",
                "Collected_Autoruns.json",
                base64.b64encode(json.dumps(results).encode("utf-8")),
            )

            siemplify.result.add_result_json(
                convert_dict_to_json_result_dict(json_results)
            )

            output_message = "Successfully collected Autoruns from the following entities:\n   {}".format(
                "\n   ".join([entity for entity in successful_entities])
            )

            if missing_entities:
                output_message += "\n\nThe following entities didn't match an any endpoint and were skipped:\n   {}".format(
                    "\n   ".join([entity for entity in missing_entities])
                )

            if failed_entities:
                output_message += "\n\nError occurred while initiating Autoruns collection on the following entities:\n   {}".format(
                    "\n   ".join([entity for entity in failed_entities])
                )

        else:
            siemplify.LOGGER.info(
                f"Investigation {investigation_id} has not completed yet. Waiting"
            )
            output_message = (
                f"Investigation {investigation_id} has not completed yet. Waiting"
            )
            result_value = siemplify.parameters["additional_data"]
            status = EXECUTION_STATE_INPROGRESS

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


def match_results_to_entity(machine_ids, results):
    """
    Match the task results to the entity that it connected to
    :param machine_ids: {dict} Mapping of endpoint machine ids to the entities identifiers
    :param results: {list} The results of the task
    :return: {dict} Mapping of entity to its results
    """
    results_by_entity = {}

    for result in results:
        entity_identifier = machine_ids.get(result.get("machine_id"))

        if entity_identifier not in results_by_entity:
            results_by_entity[entity_identifier] = [result]

        else:
            results_by_entity[entity_identifier].append(result)

    return results_by_entity


def result_to_csv(result):
    # TODO: Create a datamodel for this type of result and move this method there
    return {
        "Name": result.get("file_name"),
        "File Path": result.get("file_path"),
        "Source Location": result.get("source_location"),
        "Description": result.get("file_description"),
        "Signature Status": result.get("signature_status"),
        "Malware Score": result.get("malware_classification", {}).get("score"),
        "Arguments": result.get("arguments"),
        "Category": result.get("category"),
        "Repeat Offender": result.get("repeat_offender"),
        "MD5": result.get("hashes", {}).get("md5"),
        "SHA1": result.get("hashes", {}).get("sha1"),
        "SHA256": result.get("hashes", {}).get("sha256"),
    }


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        async_action()
