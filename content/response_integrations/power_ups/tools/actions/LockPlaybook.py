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

from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
    EXECUTION_STATE_FAILED,
    EXECUTION_STATE_INPROGRESS,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_case_overview_details

WF_STATUS_NONE = 0
WF_STATUS_INPROGRESS = 1
WF_STATUS_COMPLETED = 2
WF_STATUS_FAILED = 3
WF_STATUS_TERMINATED = 4
WF_STATUS_PENDING_IN_QUEUE = 5
WF_STATUS_PENDING_FOR_USER = 6


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = "Lock Playbook"
    case = get_case_overview_details(
        chronicle_soar=siemplify,
        case_id=siemplify.case_id,
    ).to_json()
    current_alert_index = None
    alerts = sorted(
        case["alertCards"],
        key=lambda x: x["creationTimeUnixTimeInMs"],
        reverse=True,
    )
    if siemplify.current_alert.identifier == siemplify.case.alerts[-1].identifier:
        output_message = (
            f"Alert Index: {current_alert_index}. "
            f"Alert Id: {siemplify.current_alert.identifier}: First alert - "
            "continuing playbook."
        )
        result_value = "true"
        status = EXECUTION_STATE_COMPLETED
    else:
        for alert_index, alert in enumerate(alerts):
            if alert["identifier"] == siemplify.alert_id:
                current_alert_index = alert_index
                siemplify.LOGGER.info(
                    f"alert id: {siemplify.alert_id} alert index: {current_alert_index}",
                )
                break
        if current_alert_index is not None:
            if siemplify.current_alert.identifier == siemplify.case.alerts[-1].identifier:
                output_message = (
                    f"Alert Index: {current_alert_index}. Alert Id: "
                    f"{siemplify.current_alert.identifier}: "
                    "First alert - continuing playbook."
                )
                result_value = "true"
                status = EXECUTION_STATE_COMPLETED
            elif alerts[current_alert_index - 1]["workflowsStatus"] == WF_STATUS_INPROGRESS:
                prev_case = alerts[current_alert_index - 1]["identifier"]
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
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
