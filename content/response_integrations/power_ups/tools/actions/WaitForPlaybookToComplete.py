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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_INPROGRESS
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_workflow_instance_card

from ..core.ToolsCommon import ExecutionScope

WF_STATUS_NONE = 0
WF_STATUS_INPROGRESS = 1
WF_STATUS_COMPLETED = 2
WF_STATUS_FAILED = 3
WF_STATUS_TERMINATED = 4
WF_STATUS_PENDING_IN_QUEUE = 5
WF_STATUS_PENDING_FOR_USER = 6


def get_wf_status(
    siemplify: SiemplifyAction,
    workflow_name: str,
    alert_identifier: str,
) -> int:
    """Get workflow status for a specific alert.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction object.
        workflow_name (str): Playbook name.
        alert_identifier (str): Alert identifier.

    Returns:
        int: playbook execution status.

    """
    alert_wfs_res: list[dict[str, Any]] = get_workflow_instance_card(
        chronicle_soar=siemplify,
        case_id=siemplify.case_id,
        alert_identifier=alert_identifier,
    )
    for alert_wf in alert_wfs_res:
        if alert_wf["name"] == workflow_name:
            return alert_wf["status"]

    return WF_STATUS_NONE


@output_handler
def main():
    siemplify: SiemplifyAction = SiemplifyAction()
    siemplify.script_name = "Wait for Playbook to Complete"
    playbook_name: str | None = siemplify.parameters.get("Playbook Name", None)

    execution_scope: ExecutionScope = getattr(
        siemplify, "execution_scope", ExecutionScope.Alert
    )

    output_message: str = ""
    result_value: str = "true"
    status: int = EXECUTION_STATE_COMPLETED

    if execution_scope.value == ExecutionScope.Alert.value:
        wf_status: int = get_wf_status(
            siemplify,
            playbook_name,
            siemplify.current_alert.alert_group_identifier,
        )

        if wf_status == WF_STATUS_COMPLETED:
            output_message = (
                f"Alert Id: {siemplify.current_alert.identifier}, Playbook: "
                f"{playbook_name} Finished. Lock Released. "
            )
            result_value = "true"
            status = EXECUTION_STATE_COMPLETED

        elif wf_status == WF_STATUS_FAILED:
            output_message = (
                f"Alert Id: {siemplify.current_alert.identifier}, Playbook: "
                f"{playbook_name} Failed. Lock Released. "
            )
            result_value = "true"
            status = EXECUTION_STATE_COMPLETED

        elif wf_status == WF_STATUS_TERMINATED:
            output_message = (
                f"Alert Id: {siemplify.current_alert.identifier}, Playbook: "
                f"{playbook_name} terminated. Lock Released. "
            )
            result_value = "true"
            status = EXECUTION_STATE_COMPLETED

        elif wf_status in (
            WF_STATUS_INPROGRESS,
            WF_STATUS_PENDING_FOR_USER,
            WF_STATUS_PENDING_IN_QUEUE,
        ):
            output_message = (
                f"Alert Id: {siemplify.current_alert.identifier}: "
                f"Playbook {playbook_name} Inprogress. Current playbook locked."
            )
            result_value = "false"
            status = EXECUTION_STATE_INPROGRESS

        else:
            output_message = (
                f"Alert Id: {siemplify.current_alert.identifier}: Playbook "
                f"{playbook_name} not found."
            )
            result_value = "true"
            status = EXECUTION_STATE_COMPLETED

    else:  # Case Scope
        in_progress_count: int = 0
        completed_count: int = 0
        not_found_count: int = 0

        case_alerts = getattr(siemplify.case, "open_alerts", siemplify.case.alerts)
        for alert in case_alerts:
            wf_status: int = get_wf_status(
                siemplify,
                playbook_name,
                alert.alert_group_identifier,
            )
            if wf_status in (
                WF_STATUS_INPROGRESS,
                WF_STATUS_PENDING_FOR_USER,
                WF_STATUS_PENDING_IN_QUEUE,
            ):
                in_progress_count += 1
            elif wf_status in (
                WF_STATUS_COMPLETED,
                WF_STATUS_FAILED,
                WF_STATUS_TERMINATED,
            ):
                completed_count += 1
            else:
                not_found_count += 1

        if in_progress_count > 0:
            output_message = (
                f"Playbook {playbook_name} Inprogress for {in_progress_count} alert(s)."
                " Current playbook locked."
            )
            result_value = "false"
            status = EXECUTION_STATE_INPROGRESS
        elif completed_count > 0 or not_found_count == len(case_alerts):
            output_message = (
                f"Playbook {playbook_name} Finished or not found for all alerts. Lock "
                "Released."
            )
            result_value = "true"
            status = EXECUTION_STATE_COMPLETED
        else:
            output_message = f"Playbook {playbook_name} not found for any alerts."
            result_value = "true"
            status = EXECUTION_STATE_COMPLETED

    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
