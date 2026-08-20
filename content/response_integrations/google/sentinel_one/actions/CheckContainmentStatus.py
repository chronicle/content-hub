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
from typing import Optional

try:
    from soar_sdk.SiemplifyAction import SiemplifyAction
    from soar_sdk.SiemplifyUtils import output_handler
    from soar_sdk.ScriptResult import (
        EXECUTION_STATE_COMPLETED,
        EXECUTION_STATE_FAILED,
    )
except ImportError:
    from SiemplifyAction import SiemplifyAction
    from SiemplifyUtils import output_handler
    from ScriptResult import (
        EXECUTION_STATE_COMPLETED,
        EXECUTION_STATE_FAILED,
    )

from TIPCommon import extract_action_param, extract_configuration_param

try:
    from ..core.SentinelOneResponseManager import SentinelOneResponseManager
    from ..core.exceptions import (
        SentinelOneException,
        SentinelOneNotFoundError,
    )
except ImportError:
    from SentinelOneResponseManager import SentinelOneResponseManager
    from exceptions import (
        SentinelOneException,
        SentinelOneNotFoundError,
    )

PROVIDER_NAME = "SentinelOne"
SCRIPT_NAME = "Check Containment Status"
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


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    siemplify.LOGGER.info("----------------- Main - Starting -----------------")

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
        "endpoint_containment_status": {},
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

        json_result["endpoint_containment_status"][agent_id] = {
            "status": None,
            "network_status": None,
            "reason": None,
            "agent_details": {},
        }

        manager = get_manager(siemplify)

        siemplify.LOGGER.info(f"Fetching agent details for UUID: {agent_id}")
        found_agent = manager.get_agent_by_uuid(agent_id)
        containment_status = manager.get_containment_status(found_agent.network_status)
        agent_details = (
            found_agent.to_json()
            if hasattr(found_agent, "to_json")
            else found_agent.__dict__
        )

        json_result["endpoint_containment_status"][agent_id] = {
            "status": containment_status,
            "network_status": found_agent.network_status,
            "reason": None,
            "agent_details": agent_details,
        }

        output_message = f"Successfully checked containment status for endpoint '{agent_id}'. Status: {containment_status}."
        action_status = EXECUTION_STATE_COMPLETED
        is_success = True
        siemplify.LOGGER.info(output_message)

    except SentinelOneNotFoundError as e:
        output_message = f"Could not find endpoint '{agent_id}' in SentinelOne."
        siemplify.LOGGER.error(output_message)
        if agent_id:
            if agent_id not in json_result["endpoint_containment_status"]:
                json_result["endpoint_containment_status"][agent_id] = {}
            json_result["endpoint_containment_status"][agent_id]["status"] = "unknown"
            json_result["endpoint_containment_status"][agent_id]["network_status"] = None
            json_result["endpoint_containment_status"][agent_id]["reason"] = (
                "Could not find endpoint in SentinelOne"
            )
            json_result["endpoint_containment_status"][agent_id]["agent_details"] = {}
        action_status = EXECUTION_STATE_FAILED
        is_success = False

    except Exception as e:
        output_message = f"Error executing action '{SCRIPT_NAME}'. Reason: {e}"
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        if agent_id:
            if agent_id not in json_result["endpoint_containment_status"]:
                json_result["endpoint_containment_status"][agent_id] = {}
            json_result["endpoint_containment_status"][agent_id]["status"] = "unknown"
            json_result["endpoint_containment_status"][agent_id]["network_status"] = None
            json_result["endpoint_containment_status"][agent_id]["reason"] = str(e)
            json_result["endpoint_containment_status"][agent_id]["agent_details"] = {}
        action_status = EXECUTION_STATE_FAILED
        is_success = False

    siemplify.result.add_result_json(json_result)
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {action_status}\n  is_success: {is_success}\n  output_message: {output_message}"
    )
    siemplify.end(output_message, is_success, action_status)


if __name__ == "__main__":
    main()
