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

from enum import Enum
from typing import TYPE_CHECKING, Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.constants import INTEGRATION_NAME, CREATE_REQUEST_ALERT_ACTION, CREATE_REQUEST_TYPE
from ..core.service_desk_plus_manager_v3 import service_desk_plus_manager_v3

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


@output_handler
def main() -> None:
    siemplify: SiemplifyAction = SiemplifyAction()
    siemplify.script_name = CREATE_REQUEST_ALERT_ACTION
    siemplify.LOGGER.info("----------------- Main - Param Init -----------------")

    api_root = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Root",
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Api Key",
    )
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name=INTEGRATION_NAME,
        param_name="Verify SSL",
        default_value=False,
        input_type=bool,
    )

    subject = extract_action_param(
        siemplify,
        param_name="Subject",
        is_mandatory=True,
        input_type=str,
    )
    requester = extract_action_param(
        siemplify,
        param_name="Requester",
        is_mandatory=True,
        input_type=str,
    )
    assets = extract_action_param(
        siemplify,
        param_name="Assets",
        is_mandatory=False,
        input_type=str,
        default_value="",
    ).split(",")
    status = extract_action_param(
        siemplify,
        param_name="Status",
        is_mandatory=False,
        input_type=str,
    )
    technician = extract_action_param(
        siemplify,
        param_name="Technician",
        is_mandatory=False,
        input_type=str,
    )
    priority = extract_action_param(
        siemplify,
        param_name="Priority",
        is_mandatory=False,
        input_type=str,
    )
    urgency = extract_action_param(
        siemplify,
        param_name="Urgency",
        is_mandatory=False,
        input_type=str,
    )
    category = extract_action_param(
        siemplify,
        param_name="Category",
        is_mandatory=False,
        input_type=str,
    )
    request_template = extract_action_param(
        siemplify,
        param_name="Request Template",
        is_mandatory=False,
        input_type=str,
    )
    request_type = extract_action_param(
        siemplify,
        param_name="Request Type",
        is_mandatory=False,
        input_type=str,
    )
    due_by_time = extract_action_param(
        siemplify,
        param_name="Due By Time (ms)",
        is_mandatory=False,
        input_type=int,
    )
    mode = extract_action_param(
        siemplify,
        param_name="Mode",
        is_mandatory=False,
        input_type=str,
    )
    level = extract_action_param(
        siemplify,
        param_name="Level",
        is_mandatory=False,
        input_type=str,
    )
    site = extract_action_param(
        siemplify,
        param_name="Site",
        is_mandatory=False,
        input_type=str,
    )
    group = extract_action_param(
        siemplify,
        param_name="Group",
        is_mandatory=False,
        input_type=str,
    )
    impact = extract_action_param(
        siemplify,
        param_name="Impact",
        is_mandatory=False,
        input_type=str,
    )

    params: SingleJson = {
        "subject": subject,
        "requester": requester,
        "assets": assets,
        "status": status,
        "technician": technician,
        "priority": priority,
        "urgency": urgency,
        "category": category,
        "request_template": request_template,
        "request_type": request_type,
        "due_by_time": due_by_time,
        "mode": mode,
        "level": level,
        "site": site,
        "group": group,
        "impact": impact,
    }

    siemplify.LOGGER.info("----------------- Main - Started -----------------")
    status: int = EXECUTION_STATE_COMPLETED
    result_value: bool = True

    try:
        servicedesk_manager: service_desk_plus_manager_v3 = service_desk_plus_manager_v3(
            api_root=api_root,
            api_key=api_key,
            verify_ssl=verify_ssl,
        )

        execution_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert)

        if execution_scope.value == ExecutionScope.Alert.value:
            target_alerts: list = [siemplify.current_alert]
        else:
            target_alerts: list = getattr(
                siemplify.case,
                "open_alerts",
                siemplify.case.alerts,
            )

        results: list = []
        for alert in target_alerts:
            try:
                description: str = (
                    f"Siemplify Alert ID: {alert.external_id}, Siemplify Alert Name: "
                    f"{alert.name}"
                )
                result: Any = _create_request(servicedesk_manager, description, params)
                results.append(result.to_json())
            except Exception as e:
                siemplify.LOGGER.error(f"Failed to create request for alert {alert.identifier}: {e}")

        if results:
            if execution_scope.value == ExecutionScope.Alert.value:
                output_message: str = "Successfully created ServiceDesk Plus request"
            else:
                output_message: str = (
                    "Successfully created ServiceDesk Plus requests for all alerts."
                )
            siemplify.result.add_result_json(results)
        else:
            output_message: str = "Failed to create ServiceDesk Plus requests."
            status = EXECUTION_STATE_FAILED
            result_value = False

    except Exception as e:
        output_message = (
            f"Error executing action {CREATE_REQUEST_ALERT_ACTION}. Reason: {e}"
        )
        siemplify.LOGGER.error(output_message)
        siemplify.LOGGER.exception(e)
        status = EXECUTION_STATE_FAILED
        result_value = False

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.LOGGER.info(
        f"\n  status: {status}\n  result_value: {result_value}\n  output_message: "
        f"{output_message}"
    )
    siemplify.end(output_message, result_value, status)


def _create_request(
    manager: service_desk_plus_manager_v3, alert_id: str, params: SingleJson
) -> Any:
    return manager.request(
        action_type=CREATE_REQUEST_TYPE,
        request_id="",
        description=alert_id,
        subject=params.get("subject"),
        requester=params.get("requester"),
        status=params.get("status"),
        technician=params.get("technician"),
        priority=params.get("priority"),
        urgency=params.get("urgency"),
        category=params.get("category"),
        request_template=params.get("request_template"),
        request_type=params.get("request_type"),
        due_by_time=params.get("due_by_time"),
        mode=params.get("mode"),
        level=params.get("level"),
        assets=params.get("assets"),
        site=params.get("site"),
        group=params.get("group"),
        impact=params.get("impact"),
    )


if __name__ == "__main__":
    main()
