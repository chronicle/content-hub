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
from typing import Optional

try:
    from soar_sdk.SiemplifyAction import SiemplifyAction
    from soar_sdk.SiemplifyUtils import output_handler, unix_now
    from soar_sdk.ScriptResult import (
        EXECUTION_STATE_COMPLETED,
        EXECUTION_STATE_FAILED,
        EXECUTION_STATE_INPROGRESS,
        EXECUTION_STATE_TIMEDOUT,
    )
except ImportError:
    from SiemplifyAction import SiemplifyAction
    from SiemplifyUtils import output_handler, unix_now
    from ScriptResult import (
        EXECUTION_STATE_COMPLETED,
        EXECUTION_STATE_FAILED,
        EXECUTION_STATE_INPROGRESS,
        EXECUTION_STATE_TIMEDOUT,
    )

from TIPCommon import extract_action_param, extract_configuration_param

try:
    from ..core.SentinelOneResponseManager import SentinelOneResponseManager
    from ..core.exceptions import (
        SentinelOneException,
        SentinelOneNotFoundError,
        SentinelOneTimeoutException,
    )
except ImportError:
    from SentinelOneResponseManager import SentinelOneResponseManager
    from exceptions import (
        SentinelOneException,
        SentinelOneNotFoundError,
        SentinelOneTimeoutException,
    )

PROVIDER_NAME = "SentinelOne"
SCRIPT_NAME = "Uncontain Endpoint"
TIMEOUT_THRESHOLD_MS = 35000
SUPPORTED_ENTITY_TYPES = ["HOSTNAME"]


def get_manager(siemplify: SiemplifyAction) -> SentinelOneResponseManager:
    """
    Instantiate SentinelOneResponseManager using configuration parameters.

    :param siemplify: SiemplifyAction instance
    :return: SentinelOneResponseManager instance
    """
    api_root = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Api Root",
        input_type=str,
        is_mandatory=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="API Token",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    username = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Username",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    password = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Password",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=PROVIDER_NAME,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=True,
    )
    return SentinelOneResponseManager(
        api_root=api_root,
        api_token=api_token,
        username=username,
        password=password,
        verify_ssl=verify_ssl,
    )


def is_approaching_timeout(
    action_start_time: int, python_process_timeout: Optional[int]
) -> bool:
    """
    Check if action execution is approaching timeout deadline.

    :param action_start_time: Action start time in milliseconds
    :param python_process_timeout: Execution deadline in milliseconds
    :return: True if timeout is approaching, False otherwise
    """
    if not isinstance(python_process_timeout, (int, float)) or python_process_timeout <= 0:
        return False
    return unix_now() >= (python_process_timeout - TIMEOUT_THRESHOLD_MS)


@output_handler
def main(is_first_run: bool = True):
    siemplify = SiemplifyAction()
    action_start_time = unix_now()
    siemplify.script_name = SCRIPT_NAME

    mode = "Main" if is_first_run else "QueryState"
    siemplify.LOGGER.info(f"----------------- {mode} - Starting -----------------")

    fail_if_timeout = extract_action_param(
        siemplify,
        param_name="Fail If Timeout",
        input_type=bool,
        is_mandatory=False,
        default_value=False,
    )

    agent_id = extract_action_param(
        siemplify,
        param_name="Agent ID",
        input_type=str,
        is_mandatory=False,
        default_value=None,
    )
    if not agent_id:
        agent_id = extract_action_param(
            siemplify,
            param_name="Agent UUID",
            input_type=str,
            is_mandatory=False,
            default_value=None,
        )

    json_result = {
        "operation_results": {},
        "device_metadata": {},
    }

    action_status = EXECUTION_STATE_COMPLETED
    is_success = True
    output_message = ""

    try:
        if not agent_id:
            suitable_entities = [
                entity
                for entity in getattr(siemplify, "target_entities", [])
                if getattr(entity, "entity_type", None) in SUPPORTED_ENTITY_TYPES
            ]
            if len(suitable_entities) == 1:
                entity = suitable_entities[0]
                agent_id = (
                    getattr(entity, "identifier", None)
                    or getattr(entity, "original_identifier", None)
                    or str(entity)
                )
            else:
                raise ValueError(
                    "If not passing in an endpoint id, your case/alert needs to be associated "
                    f"with exactly one HOSTNAME entity containing the endpoint id. Found {len(suitable_entities)} hosts."
                )

        json_result["operation_results"][agent_id] = {
            "operation": "uncontain",
            "result": None,
            "status": None,
            "reason": None,
        }

        manager = get_manager(siemplify)

        if is_approaching_timeout(
            action_start_time, getattr(siemplify, "execution_deadline_unix_time_ms", 0)
        ):
            raise SentinelOneTimeoutException("Timeout was approached.")

        siemplify.LOGGER.info(f"Fetching agent details for UUID: {agent_id}")
        found_agent = manager.get_agent_by_uuid(agent_id)
        json_result["device_metadata"] = (
            found_agent.to_json()
            if hasattr(found_agent, "to_json")
            else found_agent.__dict__
        )

        containment_status = manager.get_containment_status(found_agent.network_status)

        if is_first_run:
            if containment_status == "uncontained":
                action_status = EXECUTION_STATE_COMPLETED
                is_success = True
                output_message = (
                    f"Endpoint '{agent_id}' is already uncontained in SentinelOne."
                )
                json_result["operation_results"][agent_id]["result"] = "success"
                json_result["operation_results"][agent_id]["status"] = "uncontained"
                json_result["operation_results"][agent_id]["reason"] = None
                siemplify.LOGGER.info(output_message)
            elif containment_status == "uncontainment_requested":
                action_status = EXECUTION_STATE_INPROGRESS
                is_success = True
                output_message = (
                    f"Waiting for uncontainment to finish for endpoint '{agent_id}'."
                )
                json_result["operation_results"][agent_id]["result"] = "success"
                json_result["operation_results"][agent_id]["status"] = (
                    "uncontainment_requested"
                )
                json_result["operation_results"][agent_id]["reason"] = None
                siemplify.LOGGER.info(output_message)
            else:
                siemplify.LOGGER.info(
                    f"Starting uncontainment for agent '{agent_id}' (ID: {found_agent.id})"
                )
                manager.connect_agent_to_network(found_agent.id)
                action_status = EXECUTION_STATE_INPROGRESS
                is_success = True
                output_message = f"Uncontainment initiated for endpoint '{agent_id}'. Waiting for uncontainment to finish."
                json_result["operation_results"][agent_id]["result"] = "success"
                json_result["operation_results"][agent_id]["status"] = (
                    "uncontainment_requested"
                )
                json_result["operation_results"][agent_id]["reason"] = None
                siemplify.LOGGER.info(output_message)
        else:
            if containment_status == "uncontained":
                action_status = EXECUTION_STATE_COMPLETED
                is_success = True
                output_message = (
                    f"Successfully uncontained endpoint '{agent_id}' in SentinelOne."
                )
                json_result["operation_results"][agent_id]["result"] = "success"
                json_result["operation_results"][agent_id]["status"] = "uncontained"
                json_result["operation_results"][agent_id]["reason"] = None
                siemplify.LOGGER.info(output_message)
            else:
                action_status = EXECUTION_STATE_INPROGRESS
                is_success = True
                output_message = (
                    f"Waiting for uncontainment to finish for endpoint '{agent_id}'."
                )
                json_result["operation_results"][agent_id]["result"] = "success"
                json_result["operation_results"][agent_id]["status"] = (
                    "uncontainment_requested"
                )
                json_result["operation_results"][agent_id]["reason"] = None
                siemplify.LOGGER.info(output_message)

    except SentinelOneNotFoundError as e:
        output_message = f"Could not find endpoint '{agent_id}' in SentinelOne."
        siemplify.LOGGER.error(output_message)
        if agent_id:
            if agent_id not in json_result["operation_results"]:
                json_result["operation_results"][agent_id] = {"operation": "uncontain"}
            json_result["operation_results"][agent_id]["result"] = "failure"
            json_result["operation_results"][agent_id]["status"] = "unknown"
            json_result["operation_results"][agent_id]["reason"] = (
                "Could not find endpoint in SentinelOne"
            )
        action_status = EXECUTION_STATE_FAILED
        is_success = False

    except SentinelOneTimeoutException as e:
        timeout_message = f"Uncontainment request timed out for endpoint '{agent_id}'."
        siemplify.LOGGER.error(timeout_message)
        if agent_id:
            if agent_id not in json_result["operation_results"]:
                json_result["operation_results"][agent_id] = {"operation": "uncontain"}
            json_result["operation_results"][agent_id]["result"] = "failure"
            json_result["operation_results"][agent_id]["reason"] = (
                "Uncontainment request timed out."
            )
            if json_result["operation_results"][agent_id].get("status") is None:
                json_result["operation_results"][agent_id]["status"] = "unknown"

        if not is_first_run:
            output_message = timeout_message
            action_status = EXECUTION_STATE_FAILED
            is_success = False
            if fail_if_timeout:
                siemplify.result.add_result_json(json_result)
                raise SentinelOneTimeoutException(output_message)
        else:
            output_message = "Action timed out before execution completed."
            action_status = EXECUTION_STATE_TIMEDOUT
            is_success = False

    except Exception as e:
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        if agent_id:
            if agent_id not in json_result["operation_results"]:
                json_result["operation_results"][agent_id] = {"operation": "uncontain"}
            json_result["operation_results"][agent_id]["result"] = "failure"
            json_result["operation_results"][agent_id]["reason"] = str(e)
            if json_result["operation_results"][agent_id].get("status") is None:
                json_result["operation_results"][agent_id]["status"] = "unknown"
        action_status = EXECUTION_STATE_FAILED
        is_success = False

    siemplify.result.add_result_json(json_result)
    siemplify.LOGGER.info(f"----------------- {mode} - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {action_status}\n  is_success: {is_success}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, is_success, action_status)


if __name__ == "__main__":
    is_first_run = len(sys.argv) < 3 or sys.argv[2] == "True"
    main(is_first_run)
