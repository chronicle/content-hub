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

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_TIMEDOUT,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime, output_handler, unix_now
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.FireEyeHXManager import FireEyeHXManager, FireEyeHXNotFoundError

INTEGRATION_NAME = "FireEyeHX"
SCRIPT_NAME = "Cancel Host Contain"
SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


def _uncontain_by_agent_id(hx_manager, agent_id_param):
    """Handle containment cancellation when Agent Id parameter is explicitly provided."""
    agent_id = str(agent_id_param).strip()
    status = EXECUTION_STATE_COMPLETED
    operation_results = {}
    host_info = None

    try:
        host_info = hx_manager.get_host_by_agent_id(agent_id)
    except FireEyeHXNotFoundError:
        pass
    except Exception:
        pass

    try:
        hx_manager.cancel_containment_by_id(agent_id)
        result_value = "true"
        output_message = f"Successfully created cancel contain host task for Agent ID: {agent_id}"
        operation_results[agent_id] = {
            "operation": "uncontainment",
            "result": "success",
            "status": "uncontained",
            "reason": None,
        }
    except Exception as e:
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to cancel contain host with Agent ID: {agent_id}. Error: {e}"
        operation_results[agent_id] = {
            "operation": "uncontainment",
            "result": "failure",
            "status": "failed",
            "reason": str(e),
        }

    json_result = {
        "operation_results": operation_results,
        "device_metadata": host_info.raw_data if host_info and hasattr(host_info, "raw_data") else {},
    }
    return output_message, result_value, status, json_result


def _uncontain_by_entities(siemplify, hx_manager):
    """Handle containment cancellation when resolving from Siemplify entities."""
    status = EXECUTION_STATE_COMPLETED
    successful_entities = []
    missing_entities = []
    failed_entities = []
    multimatch_entities = []
    output_message = ""
    result_value = "false"
    operation_results = {}
    last_host_info = None

    for entity in siemplify.target_entities:
        if unix_now() >= siemplify.execution_deadline_unix_time_ms:
            siemplify.LOGGER.error(
                f"Timed out. execution deadline ({convert_unixtime_to_datetime(siemplify.execution_deadline_unix_time_ms)}) has passed"
            )
            status = EXECUTION_STATE_TIMEDOUT
            break

        try:
            if entity.entity_type not in SUPPORTED_ENTITIES:
                siemplify.LOGGER.info(f"Entity {entity.identifier} is of unsupported type. Skipping.")
                continue

            siemplify.LOGGER.info(f"Started processing entity: {entity.identifier}")
            matching_hosts = []

            if entity.entity_type == EntityTypes.HOSTNAME:
                siemplify.LOGGER.info(f"Fetching host for hostname {entity.identifier}")
                matching_hosts = hx_manager.get_hosts(host_name=entity.identifier)

            elif entity.entity_type == EntityTypes.ADDRESS:
                siemplify.LOGGER.info(f"Fetching host for address {entity.identifier}")
                matching_hosts = hx_manager.get_hosts_by_ip(ip_address=entity.identifier)

            if len(matching_hosts) > 1:
                siemplify.LOGGER.info(
                    f"Multiple hosts matching entity {entity.identifier} were found. First will be used."
                )
                multimatch_entities.append(entity)

            if not matching_hosts:
                siemplify.LOGGER.info("Matching host was not found for entity.")
                missing_entities.append(entity)
                operation_results[entity.identifier] = {
                    "operation": "uncontainment",
                    "result": "failure",
                    "status": "failed",
                    "reason": "Host not found",
                }
                continue

            host = max(matching_hosts, key=lambda matching_host: matching_host.last_poll_timestamp)
            last_host_info = host
            siemplify.LOGGER.info(f"Matching host was found for {entity.identifier}")

            siemplify.LOGGER.info(f"Initiating cancel containment of host {host._id} ({entity.identifier})")
            hx_manager.cancel_containment_by_id(host._id)

            successful_entities.append(entity)
            operation_results[entity.identifier] = {
                "operation": "uncontainment",
                "result": "success",
                "status": "uncontained",
                "reason": None,
            }
            siemplify.LOGGER.info(f"Finished processing entity {entity.identifier}")

        except Exception as e:
            failed_entities.append(entity)
            operation_results[entity.identifier] = {
                "operation": "uncontainment",
                "result": "failure",
                "status": "failed",
                "reason": str(e),
            }
            siemplify.LOGGER.exception(f"An error occurred on entity {entity.identifier}: {e}")

    if successful_entities:
        output_message += "Successfully created cancel contain host task for the following entities:\n   {}".format(
            "\n   ".join([entity.identifier for entity in successful_entities])
        )
        result_value = "true"
    else:
        output_message += "No tasks were created."
        result_value = "false"

    if multimatch_entities:
        output_message += (
            "Multiple matches were found in FireEye HX, "
            "taking the agent info with the most recent last poll time value "
            "for the following entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in multimatch_entities])
            )
        )

    if missing_entities:
        output_message += (
            "\n\nAction was not able to find matching FireEye HX agent for the following entities:\n   {}".format(
                "\n   ".join([entity.identifier for entity in missing_entities])
            )
        )

    if failed_entities:
        output_message += "\n\nFailed processing the following entities:\n   {}".format(
            "\n   ".join([entity.identifier for entity in failed_entities])
        )

    json_result = {
        "operation_results": operation_results,
        "device_metadata": last_host_info.raw_data if last_host_info and hasattr(last_host_info, "raw_data") else {},
    }
    return output_message, result_value, status, json_result


@output_handler
def main() -> None:
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

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

    agent_id_param = extract_action_param(
        siemplify,
        param_name="Agent Id",
        is_mandatory=False,
        input_type=str,
        print_value=True,
    )

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    status = EXECUTION_STATE_COMPLETED
    output_message = ""
    result_value = "false"
    json_result = {}

    try:
        hx_manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        if agent_id_param and agent_id_param.strip():
            output_message, result_value, status, json_result = _uncontain_by_agent_id(hx_manager, agent_id_param)
        else:
            output_message, result_value, status, json_result = _uncontain_by_entities(siemplify, hx_manager)

        if json_result:
            siemplify.result.add_result_json(json_result)

    except Exception as e:
        siemplify.LOGGER.exception(f"Failed to execute action! Error is {e}")
        status = EXECUTION_STATE_FAILED
        result_value = "false"
        output_message = f"Failed to execute action! Error is {e}"

    finally:
        try:
            hx_manager.logout()
        except Exception as e:
            siemplify.LOGGER.exception(f"Logging out failed. Error: {e}")

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(f"Status: {status}:")
    siemplify.LOGGER.info(f"Result Value: {result_value}")
    siemplify.LOGGER.info(f"Output Message: {output_message}")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
