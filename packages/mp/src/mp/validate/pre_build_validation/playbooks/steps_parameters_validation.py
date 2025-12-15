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

from dataclasses import dataclass
from typing import TYPE_CHECKING

from mp.core.data_models.playbooks.step.metadata import Step
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


MIN_ASYNC_POLLING_INTERVAL_IN_SECONDS: int = 30
MIN_PENDING_ACTION_TIMEOUT: int = 300
MAX_ASYNC_ACTION_TIMEOUT: int = 1209600


@dataclass(slots=True, frozen=True)
class StepParamsValidation:
    name: str = "Step Parameters Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        """Run validation on all steps parameters within a playbook.

        Args:
            playbook_path: The path to the non-built playbook directory.

        Raises:
            NonFatalValidationError: If any step parameter validation fails.

        """
        validation_result: list[dict[str, list[str]]] = []

        steps: list[Step] = Step.from_non_built_path(playbook_path)
        for step in steps:
            step_result: dict[str, list[str]] | None = _process_step(step)
            if step_result:
                validation_result.append(step_result)

        if validation_result:
            msg: str = _create_validation_msg(validation_result)
            raise NonFatalValidationError(msg)


def _process_step(step: Step) -> dict[str, list[str]] | None:  # noqa: C901
    step_result: list[str] = []

    async_action_timeout: str = ""
    async_polling_interval: str = ""

    for param in step.parameters:
        match param.name:
            case "AssignedUsers":
                if param.value and step.is_automatic:
                    step_result.append("AssignedUsers is not allowed for automatic steps.")

            case "PendingActionTimeout":
                if param.value and int(param.value) < MIN_PENDING_ACTION_TIMEOUT:
                    step_result.append("PendingActionTimeout must be at least 300 seconds.")

            case "AsyncActionTimeout":
                if param.value and not (0 < int(param.value) <= MAX_ASYNC_ACTION_TIMEOUT):
                    step_result.append(
                        "AsyncActionTimeout must positive number less than 14 days (in seconds)."
                    )
                async_action_timeout = param.value

            case "AsyncPollingInterval":
                if param.value and int(param.value) < MIN_ASYNC_POLLING_INTERVAL_IN_SECONDS:
                    step_result.append("AsyncPollingInterval must be at least 30 seconds.")
                async_polling_interval = param.value

    if (
        async_action_timeout
        and async_polling_interval
        and int(async_polling_interval) > int(async_action_timeout)
    ):
        step_result.append("AsyncPollingInterval must be less than AsyncActionTimeout.")

    return {step.instance_name: step_result} if step_result else None


def _create_validation_msg(validation_result: list[dict[str, list[str]]]) -> str:
    msg_lines: list[str] = []
    for item in validation_result:
        for step_name, errors in item.items():
            msg_lines.append(f"Step name: {step_name}")
            msg_lines.extend(errors)

    return "\n".join(msg_lines)
