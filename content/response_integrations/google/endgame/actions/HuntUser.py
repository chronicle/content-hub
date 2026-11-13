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
import sys
from soar_sdk.SiemplifyAction import SiemplifyAction
from ..core.EndgameManager import EndgameManager, EndgameNotFoundError
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_INPROGRESS,
    EXECUTION_STATE_FAILED,
)
from TIPCommon import extract_configuration_param, extract_action_param
from ..core.EndgameCommon import EndgameCommon
import sys
import json


INTEGRATION_NAME = "Endgame"
SCRIPT_NAME = "Hunt User"
INVESTIGATIOM_NAME = "Siemplify User Hunt Investigation API"
DEFAULT_CORE_OS = "windows"
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

    investigation_name = extract_action_param(
        siemplify,
        param_name="Investigation Name",
        is_mandatory=False,
        input_type=str,
        default_value=INVESTIGATIOM_NAME,
        print_value=True,
    )

    core_os = extract_action_param(
        siemplify,
        param_name="Endpoints Core OS",
        is_mandatory=False,
        input_type=str,
        default_value=DEFAULT_CORE_OS,
        print_value=True,
    )

    find_usernames = extract_action_param(
        siemplify,
        param_name="Find Username",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )
    find_usernames = (
        [find_username.strip() for find_username in find_usernames.split(",")]
        if find_usernames
        else []
    )

    domain_name = extract_action_param(
        siemplify,
        param_name="Domain Name",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    sensor_ids = []
    successful_entities = []
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

                if endpoint.core_os.lower() != core_os:
                    siemplify.LOGGER.info(
                        f"Endpoint {entity.identifier} OS doesn't match passed core OS. Skipping."
                    )
                    continue

                if endpoint.sensors:
                    successful_entities.append(entity.identifier)
                    sensor_ids.extend([sensor.id for sensor in endpoint.sensors])

            except Exception as e:
                failed_entities.append(entity.identifier)
                siemplify.LOGGER.error(
                    f"An error occurred on entity {entity.identifier}"
                )
                siemplify.LOGGER.exception(e)

        if successful_entities:
            siemplify.LOGGER.info(
                "Initiating user hunt task on the following entities: {}".format(
                    "\n   ".join([entity for entity in successful_entities])
                )
            )

            task_id = endgame_manager.get_task_id("iocSearchRequest", core_os)
            task = endgame_manager.create_ioc_username_search_task(
                find_username=find_usernames, domain=domain_name
            )

            # By default, the investigation is assigned to the login user
            investigation_id = endgame_manager.create_investigation(
                investigation_name=investigation_name,
                assign_user=username,
                sensor_ids=sensor_ids,
                tasks={task_id: {"task_list": [task]}},
                core_os=core_os,
            )

            siemplify.LOGGER.info(
                f"Successfully Create investigation with ID {investigation_id}"
            )

            if successful_entities:
                output_message += "Successfully initiated user hunt on the following entities:\n   {}".format(
                    "\n   ".join([entity for entity in successful_entities])
                )

            if missing_entities:
                output_message += "\n\nThe following entities didn't match an any endpoint and were skipped:\n   {}".format(
                    "\n   ".join([entity for entity in missing_entities])
                )

            if failed_entities:
                output_message += "\n\nError occurred while initiating user hunt on the following entities:\n   {}".format(
                    "\n   ".join([entity for entity in failed_entities])
                )

            output_message += f"\n\nInvestigation ID: {investigation_id}. Waiting for investigation to complete."

            result_value = json.dumps(
                {
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


def fetch_scan_report_async():
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    endgame_common = EndgameCommon(siemplify)
    output_message, return_value, status = endgame_common.fetch_investigation_result()
    siemplify.end(output_message, return_value, status)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[2] == "True":
        main()
    else:
        fetch_scan_report_async()
