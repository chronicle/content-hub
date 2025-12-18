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
from typing import TYPE_CHECKING

from dateutil.parser import parse
from TIPCommon.base.action import Action
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC, NUM_OF_SEC_IN_MIN
from TIPCommon.extraction import extract_action_param
from TIPCommon.rest.soar_api import (
    add_or_update_case_task_v5,
    add_or_update_case_task_v6,
)

from ..core.ToolsCommon import (
    is_supported_siemplify_version,
    parse_version_string_to_tuple,
)

if TYPE_CHECKING:
    from typing import Never, NoReturn

ACTION_NAME: str = "CreateNewTask"
CREATE_TASK_SIEMPLIFY_5X_VERSION: str = "5.0.0.0"
CREATE_TASK_SIEMPLIFY_6X_VERSION: str = "6.0.0.0"


class CreateSiemplifyTaskAction(Action):
    def __init__(self) -> None:
        super().__init__(ACTION_NAME)

    def _extract_action_parameters(self) -> None:
        self.params.assign_to = extract_action_param(
            self.soar_action,
            param_name="Assign To",
            is_mandatory=True,
            print_value=True,
        )
        self.params.task_content = extract_action_param(
            self.soar_action,
            param_name="Task Content",
            is_mandatory=True,
            print_value=True,
        )
        self.params.duration = extract_action_param(
            self.soar_action,
            param_name="SLA (in minutes)",
            is_mandatory=False,
            print_value=True,
        )
        self.params.task_title = extract_action_param(
            self.soar_action,
            param_name="Task Title",
            is_mandatory=False,
            print_value=True,
        )
        self.params.due_date = extract_action_param(
            self.soar_action,
            param_name="Due Date",
            is_mandatory=False,
            print_value=True,
        )

    def _validate_params(self) -> None:
        if not self.params.due_date and not self.params.duration:
            raise ValueError(
                'either "Due Date" or "SLA (in minutes)" parameter should have a value.'
            )

    def _init_api_clients(self) -> None:
        """Initialize API clients if required (placeholder)."""

    def _perform_action(self, __: Never) -> None:
        task_due_date: int = self._compute_due_time()
        self._create_task(task_due_date)

        due_date_info: str = (
            f"by {self.params.due_date}"
            if self.params.due_date
            else f"in the next {self.params.duration} minutes"
        )
        self.output_message = (
            f"A new task has been created for the user: {self.params.assign_to}.\n"
            f"This task should be handled {due_date_info}"
        )
        self.result_value = True

    def _compute_due_time(self) -> int:
        """Return due time in epoch millis based on given parameters."""
        if self.params.due_date:
            return int(parse(self.params.due_date).timestamp() * NUM_OF_MILLI_IN_SEC)

        minutes: int = int(self.params.duration)
        return (
            int(time.time() * NUM_OF_MILLI_IN_SEC)
            + minutes * NUM_OF_SEC_IN_MIN * NUM_OF_MILLI_IN_SEC
        )

    def _create_task(self, task_due_date: int) -> None:
        current_version = self.soar_action.get_system_version()

        if is_supported_siemplify_version(
            parse_version_string_to_tuple(current_version),
            parse_version_string_to_tuple(CREATE_TASK_SIEMPLIFY_6X_VERSION),
        ):
            add_or_update_case_task_v5(
                self.soar_action,
                owner=self.params.assign_to,
                title=self.params.task_title,
                content=self.params.task_content,
                due_date_unix_time_ms=task_due_date,
                case_id=self.soar_action.case_id,
            )
        elif is_supported_siemplify_version(
            parse_version_string_to_tuple(current_version),
            parse_version_string_to_tuple(CREATE_TASK_SIEMPLIFY_5X_VERSION),
        ):
            add_or_update_case_task_v6(
                self.soar_action,
                owner=self.params.assign_to,
                title=self.params.task_title,
                content=self.params.task_content,
                due_date_unix_time_ms=task_due_date,
                case_id=self.soar_action.case_id,
            )


def main() -> NoReturn:
    CreateSiemplifyTaskAction().run()


if __name__ == "__main__":
    main()
