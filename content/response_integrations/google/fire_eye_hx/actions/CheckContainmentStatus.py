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
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyDataModel import EntityTypes
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon import extract_action_param, extract_configuration_param

from ..core.FireEyeHXManager import FireEyeHXManager, FireEyeHXNotFoundError

INTEGRATION_NAME = "FireEyeHX"
SCRIPT_NAME = "Check Containment Status"
SUPPORTED_ENTITIES = [EntityTypes.ADDRESS, EntityTypes.HOSTNAME]


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
    operation_results = {}
    host_info = None

    try:
        hx_manager = FireEyeHXManager(
            api_root=api_root,
            username=username,
            password=password,
            verify_ssl=verify_ssl,
        )

        agent_id = hx_manager.resolve_agent_id_from_entities(
            target_entities=siemplify.target_entities,
            agent_id_param=agent_id_param,
        )

        if not agent_id:
            output_message = "No Agent ID was provided or could be resolved from entities."
            status = EXECUTION_STATE_FAILED
            result_value = "false"
        else:
            try:
                host_info = hx_manager.get_host_by_agent_id(agent_id)
            except FireEyeHXNotFoundError:
                pass
            except Exception:
                pass

            try:
                state = getattr(host_info, "containment_state", None)
                if not state:
                    containment_data = hx_manager.get_containment_status(agent_id)
                    state = (
                        containment_data.get("state", "unknown")
                        if isinstance(containment_data, dict)
                        else str(containment_data)
                    )
                if state == "normal":
                    state = "uncontained"
                output_message = f"Host with Agent ID {agent_id} containment status: {state}"
                result_value = state
                operation_results[agent_id] = {
                    "operation": "containment_status",
                    "result": "success",
                    "status": state,
                    "reason": None,
                }
            except Exception as e:
                output_message = f"Failed to get containment status for Agent ID: {agent_id}. Error: {e}"
                status = EXECUTION_STATE_FAILED
                result_value = "false"
                operation_results[agent_id] = {
                    "operation": "containment_status",
                    "result": "failure",
                    "status": "failed",
                    "reason": str(e),
                }

        json_result = {
            "operation_results": operation_results,
            "device_metadata": host_info.raw_data if host_info and hasattr(host_info, "raw_data") else {},
        }
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
