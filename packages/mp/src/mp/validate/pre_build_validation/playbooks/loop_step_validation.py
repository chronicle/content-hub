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

from mp.core.data_models.playbooks.step.metadata import Step, StepType
from mp.core.exceptions import FatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, frozen=True)
class LoopStepValidation:
    name: str = "Loop Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        """Validate that all loops in a playbook are properly opened and closed.

        Args:
            playbook_path: The path to the playbook file.

        Raises:
            FatalValidationError: If there are any loop validation errors.

        """
        steps: list[Step] = Step.from_non_built_path(playbook_path)
        balance: int = 0
        error_msgs: list[str] = []

        end_loop_start_ids = {
            step.start_loop_step_id
            for step in steps
            if step.type_ is StepType.FOR_EACH_END_LOOP and step.start_loop_step_id is not None
        }

        for step in steps:
            if step.type_ is StepType.FOR_EACH_START_LOOP:
                if step.start_loop_step_id not in end_loop_start_ids:
                    error_msgs.append(
                        f"Step <{step.instance_name}> is missing a matching end loop step"
                    )
                balance += 1
            elif step.type_ is StepType.FOR_EACH_END_LOOP:
                balance -= 1

        if balance < 0:
            error_msgs.append(f"There are missing {abs(balance)} start loop steps.")
        elif balance > 0:
            error_msgs.append(f"There are missing {balance} end loop steps.")

        if error_msgs:
            raise FatalValidationError(",\n".join(error_msgs) + "\n")
