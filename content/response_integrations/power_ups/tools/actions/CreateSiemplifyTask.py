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

import time

from dateutil.parser import parse
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.ToolsCommon import (
    is_supported_siemplify_version,
    parse_version_string_to_tuple,
)

X5_TASK_URL = "{}/external/v1/cases/AddOrUpdateCaseTask"
X6_TASK_URL = "{}/external/v1/sdk/AddOrUpdateCaseTask"
ACTION_NAME = "CreateNewTask"
CREATE_TASK_SIEMPLIFY_5X_VERSION = "5.0.0.0"
CREATE_TASK_SIEMPLIFY_6X_VERSION = "6.0.0.0"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = ACTION_NAME

    assign_to = siemplify.extract_action_param(
        param_name="Assign To",
        is_mandatory=True,
        print_value=True,
    )
    task_content = siemplify.extract_action_param(
        param_name="Task Content",
        is_mandatory=True,
        print_value=True,
    )
    duration = siemplify.extract_action_param(
        param_name="SLA (in minutes)",
        is_mandatory=False,
        print_value=True,
    )
    task_title = siemplify.extract_action_param(
        param_name="Task Title",
        is_mandatory=False,
        print_value=True,
    )
    due_date = siemplify.extract_action_param(
        param_name="Due Date",
        is_mandatory=False,
        print_value=True,
    )

    if not due_date and not duration:
        raise ValueError(
            'either "Due Date" or "SLA (in minutes)" parameter should have value.'
        )

    client_time = 0
    if due_date:
        dt_due_date = parse(due_date)
        client_time = int(dt_due_date.timestamp() * 1000)
    elif duration:
        time_now_epoch = int(time.time() * 1000)
        client_time = time_now_epoch + (int(duration) * 1000 * 60)

    current_version = siemplify.get_system_version()
    json_payload = {}
    task_url = ""

    if is_supported_siemplify_version(
        parse_version_string_to_tuple(current_version),
        parse_version_string_to_tuple(CREATE_TASK_SIEMPLIFY_6X_VERSION),
    ):
        json_payload = {
            "owner": assign_to,
            "content": task_content,
            "dueDate": "",
            "dueDateUnixTimeMs": client_time,
            "title": task_title,
            "caseId": siemplify.case_id,
        }
        task_url = X6_TASK_URL
    elif is_supported_siemplify_version(
        parse_version_string_to_tuple(current_version),
        parse_version_string_to_tuple(CREATE_TASK_SIEMPLIFY_5X_VERSION),
    ):
        json_payload = {
            "owner": assign_to,
            "name": task_content,
            "dueDate": "",
            "dueDateUnixTimeMs": client_time,
            "caseId": siemplify.case_id,
        }
        task_url = X5_TASK_URL

    add_task = siemplify.session.post(
        task_url.format(siemplify.API_ROOT),
        json=json_payload,
    )
    add_task.raise_for_status()

    due_date_info = (
        f"by {due_date}" if due_date else f"in the next {duration} minutes"
    )
    output_message = (
        f"A new task has been created for the user: {assign_to}.\n"
        f"This task should be handled {due_date_info}"
    )
    siemplify.end(output_message, True)


if __name__ == "__main__":
    main()
