# Copyright 2025 Google LLC
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

from typing import Any

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_workflow_instance_card

from ..core.ToolsCommon import ExecutionScope, get_case_alerts

WF_STATUS_NONE = 0
WF_STATUS_INPROGRESS = 1
WF_STATUS_COMPLETED = 2
WF_STATUS_FAILED = 3
WF_STATUS_TERMINATED = 4
WF_STATUS_PENDING_IN_QUEUE = 5
WF_STATUS_PENDING_FOR_USER = 6


def are_playbooks_complete(siemplify: SiemplifyAction, alert_group_id: str) -> bool:
    """Get workflow status for current alert.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        alert_group_id (str): alert group identifier.

    Returns:
        int: playbook execution status.
    """
    alert_wfs_res = get_workflow_instance_card(
        chronicle_soar=siemplify,
        case_id=siemplify.case_id,
        alert_identifier=alert_group_id,
    )
    statuses = map(lambda x: x["status"] == WF_STATUS_COMPLETED, alert_wfs_res)
    return all(statuses)


@output_handler
def main():
    siemplify: SiemplifyAction = SiemplifyAction()
    siemplify.script_name = "Lock Playbook"
    
    execution_scope: ExecutionScope = getattr(
        siemplify, "execution_scope", ExecutionScope.Alert
    )
    
    output_message: str = ""
    result_value: str = "false"
    status: int = EXECUTION_STATE_FAILED
    
    if execution_scope.value == ExecutionScope.Alert.value:
        case: Any = siemplify.case
        current_alert_index: int | None = None
        case_alerts = case.alerts
        alerts: list = list(sorted(
            case_alerts,
            key=lambda x: x.creation_time,
        ))

        for alert_index, alert in enumerate(alerts):
            if alert.identifier == siemplify.alert_id:
                current_alert_index = alert_index
                siemplify.LOGGER.info(
                    f"Alert id: {siemplify.alert_id} alert index: {current_alert_index}"
                )
                break
        if current_alert_index == 0:
            output_message = (
                f"Alert Index: {current_alert_index}. "
                f"Alert Id: {siemplify.current_alert.identifier}: First alert - "
                "continuing playbook."
            )
            result_value = "true"
            status = EXECUTION_STATE_COMPLETED
        elif current_alert_index is not None:
            previous_alert = alerts[current_alert_index - 1]
            previous_alert_group_identifier = previous_alert.alert_group_identifier
            if not are_playbooks_complete(siemplify, previous_alert_group_identifier):
                prev_case = previous_alert.identifier
                output_message = (
                    f"Alert Index: {current_alert_index}. Alert Id: "
                    f"{siemplify.current_alert.identifier}: Playbook Locked. "
                    f"Waiting for alert # {prev_case} playbook to finish."
                )
                result_value = "false"
                status = EXECUTION_STATE_INPROGRESS
            else:
                output_message = (
                    f"Alert Index: {current_alert_index}. Alert Id: "
                    f"{siemplify.current_alert.identifier}: Lock Released. "
                )
                result_value = "true"
                status = EXECUTION_STATE_COMPLETED
        else:
            status = EXECUTION_STATE_FAILED
            output_message = "Couldn't find current alert"
            result_value = "false"
            
    else:
        all_complete: bool = True
        waiting_for: list = []
        case_alerts = get_case_alerts(siemplify)
        for alert in case_alerts:
            if not are_playbooks_complete(siemplify, alert.alert_group_identifier):
                all_complete = False
                waiting_for.append(alert.identifier)
                
        if all_complete:
            output_message = "Lock Released. All playbooks in the case are completed."
            result_value = "true"
            status = EXECUTION_STATE_COMPLETED
        else:
            output_message = (
                "Playbook Locked. Waiting for playbooks to finish for alerts: "
                f"{', '.join(waiting_for)}"
            )
            result_value = "false"
            status = EXECUTION_STATE_INPROGRESS
        
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
