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

from typing import TYPE_CHECKING

from enum import Enum

from soar_sdk.SiemplifyUtils import output_handler
from soar_sdk.SiemplifyUtils import convert_unixtime_to_datetime
from soar_sdk.SiemplifyAction import SiemplifyAction

from TIPCommon.extraction import extract_configuration_param, extract_action_param

from ..core.ServiceDeskPlusManager import ServiceDeskPlusManager, DUE_DATE_FORMAT


if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

TAG: str = "ServiceDeskPlus"


class ExecutionScope(Enum):
    ExecutionScopeUnspecified = 0
    Alert = 1
    Case = 2


@output_handler
def main() -> None:
    siemplify: SiemplifyAction = SiemplifyAction()
    api_root = extract_configuration_param(
        siemplify,
        provider_name=TAG,
        param_name="Api Root",
    )
    api_key = extract_configuration_param(
        siemplify,
        provider_name=TAG,
        param_name="Api Key",
    )

    service_desk_plus_manager: ServiceDeskPlusManager = ServiceDeskPlusManager(
        api_root, api_key
    )
    due_by_time = extract_action_param(
        siemplify, param_name="Due By Time (ms)", print_value=True
    )
    subject = extract_action_param(
        siemplify,
        param_name="Subject",
        print_value=True,
    )
    requester = extract_action_param(
        siemplify,
        param_name="Requester",
        print_value=True,
    )
    status = extract_action_param(
        siemplify,
        param_name="Status",
        print_value=True,
    )
    technician = extract_action_param(
        siemplify,
        param_name="Technician",
        print_value=True,
    )
    priority = extract_action_param(
        siemplify,
        param_name="Priority",
        print_value=True,
    )
    urgency = extract_action_param(
        siemplify,
        param_name="Urgency",
        print_value=True,
    )
    category = extract_action_param(
        siemplify,
        param_name="Category",
        print_value=True,
    )
    request_template = extract_action_param(
        siemplify,
        param_name="Request Template",
        print_value=True,
    )
    request_type = extract_action_param(
        siemplify,
        param_name="Request Type",
        print_value=True,
    )
    mode = extract_action_param(
        siemplify,
        param_name="Mode",
        print_value=True,
    )
    level = extract_action_param(
        siemplify,
        param_name="Level",
        print_value=True,
    )
    site = extract_action_param(
        siemplify,
        param_name="Site",
        print_value=True,
    )
    group = extract_action_param(
        siemplify,
        param_name="Group",
        print_value=True,
    )
    impact = extract_action_param(
        siemplify,
        param_name="Impact",
        print_value=True,
    )

    params: SingleJson = {
        "subject": subject,
        "requester": requester,
        "status": status,
        "technician": technician,
        "priority": priority,
        "urgency": urgency,
        "category": category,
        "request_template": request_template,
        "request_type": request_type,
        "due_by_time": int(due_by_time) if due_by_time else None,
        "mode": mode,
        "level": level,
        "site": site,
        "group": group,
        "impact": impact,
    }

    execution_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert)

    if execution_scope.value == ExecutionScope.Alert.value:
        target_alerts: list = [siemplify.current_alert]
    else:
        target_alerts: list = getattr(
            siemplify.case,
            "open_alerts",
            siemplify.case.alerts,
        )

    created_requests: SingleJson = {}
    for alert in target_alerts:
        try:
            req_id: str = _create_request(
                service_desk_plus_manager,
                alert.external_id,
                params,
            )
            created_requests[alert.identifier] = req_id
        except Exception as e:
            siemplify.LOGGER.error(f"Failed to create request for alert {alert.identifier}: {e}")

    siemplify.add_tag(TAG)
    siemplify.update_alerts_additional_data(created_requests)

    if created_requests:
        if execution_scope.value == ExecutionScope.Alert.value:
            request_id: str = list(created_requests.values())[0]
            output_message: str = f"ServiceDesk Plus request - {request_id} was created."
            result_value: str = request_id
        else:
            output_message: str = (
                "Successfully created requests for alerts: "
                f"{', '.join(created_requests.values())}."
            )
            result_value: str = ",".join([str(num) for num in created_requests.values()])
    else:
        output_message: str = "Failed to create ServiceDesk Plus requests."
        result_value = False

    siemplify.end(output_message, result_value)

def _create_request(
    manager: ServiceDeskPlusManager,
    alert_id: str,
    params: SingleJson,
) -> str:
    due_by_time = params.get("due_by_time")
    request_obj = manager.add_request(
        subject=params.get("subject"),
        requester=params.get("requester"),
        description=alert_id,
        status=params.get("status"),
        technician=params.get("technician"),
        priority=params.get("priority"),
        urgency=params.get("urgency"),
        category=params.get("category"),
        request_template=params.get("request_template"),
        request_type=params.get("request_type"),
        due_by_time=(
            convert_unixtime_to_datetime(due_by_time).strftime(DUE_DATE_FORMAT)
            if due_by_time
            else None
        ),
        mode=params.get("mode"),
        level=params.get("level"),
        site=params.get("site"),
        group=params.get("group"),
        impact=params.get("impact"),
    )
    return request_obj.workorderid


if __name__ == "__main__":
    main()
