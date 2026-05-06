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

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler
from TIPCommon.rest.soar_api import get_workflow_instance_card


def get_attached_workflows(siemplify):
    alert_id = None
    for alert in siemplify.case.alerts:
        if alert.identifier == siemplify.alert_id:
            alert_id = alert.additional_properties["AlertGroupIdentifier"]
            break

    alert_wfs_res = get_workflow_instance_card(
        chronicle_soar=siemplify,
        case_id=siemplify.case_id,
        alert_identifier=alert_id,
    )
    return {alert_wf["name"] for alert_wf in alert_wfs_res}


@output_handler
def main():
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

    attached_workflows = []
    not_attached = []
    duplicates = []
    output_message = ""
    is_success = True
    status = EXECUTION_STATE_COMPLETED

    previously_attached_wf = get_attached_workflows(siemplify)

    for workflow_name in workflow_names:
        if workflow_name in previously_attached_wf and not allow_duplicates:
            duplicates.append(workflow_name)
        else:
            try:
                siemplify.attach_workflow_to_case(workflow_name)
                attached_workflows.append(workflow_name)
            except Exception:
                is_success = False
                not_attached.append(workflow_name)

    if duplicates:
        output_message += (
            "The following playbooks were already attached to the alert "
            f"{siemplify.current_alert.identifier}: {', '.join(duplicates)}\n"
        )

    if len(not_attached) == len(workflow_names):
        output_message += "None of the provided playbooks were attached. Please check the spelling.\n"
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
    siemplify.end(output_message, is_success, status)


if __name__ == "__main__":
    main()
