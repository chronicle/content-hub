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

from Siemplify import Siemplify
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_workflow_instance_card

from ..core.ToolsCommon import (
    ExecutionScope,
    get_execution_scope,
    get_target_alerts,
)


def get_attached_workflows_for_alert(
    siemplify: SiemplifyAction,
    alert: Any,
) -> set[str]:
    """Retrieve the names of workflows already attached to a specific alert.

    Args:
        siemplify: The SiemplifyAction orchestration instance.
        alert: The target alert SDK instance.

    Returns:
        Set of workflow names attached to the alert.
    """
    alert_id = alert.additional_properties.get("AlertGroupIdentifier")
    if not alert_id:
        return set()
    alert_wfs_res = get_workflow_instance_card(
        chronicle_soar=siemplify,
        case_id=siemplify.case_id,
        alert_identifier=alert_id,
    )
    return set(alert_wf["name"] for alert_wf in alert_wfs_res)


@output_handler
def main() -> None:
    """Execute AttachPlaybookToAlert action."""
    siemplify = SiemplifyAction()

    allow_duplicates = siemplify.extract_action_param(
        "Allow Duplicates",
        input_type=bool,
        default_value=True,
    )
    playbook_names = siemplify.extract_action_param("Playbook Name", print_value=True)

    workflow_names = set(
        filter(
            None,
            (workflow_name.strip() for workflow_name in playbook_names.split(",")),
        ),
    )

    all_attached = []
    all_not_attached = []
    all_duplicates = []
    output_message = ""
    is_success = True
    status = EXECUTION_STATE_COMPLETED

    raw_scope = getattr(siemplify, "execution_scope", ExecutionScope.Alert.value)
    execution_scope = get_execution_scope(raw_scope, logger=siemplify.LOGGER)

    target_alerts = get_target_alerts(siemplify, execution_scope)

    for alert in target_alerts:
        try:
            previously_attached_wf = get_attached_workflows_for_alert(siemplify, alert)

            for workflow_name in workflow_names:
                if workflow_name in previously_attached_wf and not allow_duplicates:
                    all_duplicates.append((alert.identifier, workflow_name))
                else:
                    try:
                        success = Siemplify.attach_workflow_to_case(
                            siemplify,
                            workflow_name,
                            siemplify.case_id,
                            alert.identifier,
                        )
                        if success:
                            all_attached.append((alert.identifier, workflow_name))
                        else:
                            is_success = False
                            all_not_attached.append((alert.identifier, workflow_name))
                    except Exception:
                        is_success = False
                        all_not_attached.append((alert.identifier, workflow_name))
        except Exception as e:
            siemplify.LOGGER.error(
                "Failed to process playbook attachments for alert "
                f"{alert.identifier}: {e}."
            )
            is_success = False

    if execution_scope.value == ExecutionScope.Alert.value:
        duplicates = [wf for _, wf in all_duplicates]
        not_attached = [wf for _, wf in all_not_attached]
        attached_workflows = [wf for _, wf in all_attached]

        if duplicates:
            output_message += (
                "The following playbooks were already attached to the alert "
                f"{siemplify.current_alert.identifier}: {', '.join(duplicates)}\n"
            )

        if len(not_attached) == len(workflow_names):
            output_message += (
                "None of the provided playbooks were attached. "
                "Please check the spelling.\n"
            )
        elif not_attached:
            output_message += (
                "Action wasn't able to attach the following "
                f"playbooks: {', '.join(not_attached)}. Please check the spelling.\n"
            )

        if attached_workflows:
            output_message += (
                "Successfully attached the following playbooks to the "
                f"alert {siemplify.current_alert.identifier}: "
                f"{', '.join(attached_workflows)}"
            )
    else:
        if all_duplicates:
            output_message += "The following playbooks were already attached:\n"
            for alert_id, wf in all_duplicates:
                output_message += f"- Alert {alert_id}: {wf}\n"
        if all_not_attached:
            output_message += "Failed to attach the following playbooks:\n"
            for alert_id, wf in all_not_attached:
                output_message += f"- Alert {alert_id}: {wf}\n"
        if all_attached:
            output_message += "Successfully attached the following playbooks:\n"
            for alert_id, wf in all_attached:
                output_message += f"- Alert {alert_id}: {wf}\n"

    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
