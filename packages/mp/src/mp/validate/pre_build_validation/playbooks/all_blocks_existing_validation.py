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
from mp.core.utils import get_all_blocks_id_from_path

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, frozen=True)
class AllBlocksExistValidation:
    name: str = "All Blocks Exist Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        """Check that all blocks that are part of a playbook are existing in the content-hub.

        Args:
            playbook_path: The path to the playbook.

        Raises:
            FatalValidationError: If any referenced blocks are missing.

        """
        required_block_ids: set[str] = set()
        steps: list[Step] = Step.from_non_built_path(playbook_path)
        for step in steps:
            if step.type_ is not StepType.BLOCK:
                continue

            for parm in step.parameters:
                if parm.name == "NestedWorkflowIdentifier":
                    block_id: str | None = parm.value
                    if block_id is None:
                        continue
                    required_block_ids.add(block_id)
                    break

        if not required_block_ids:
            return

        available_block_ids = get_all_blocks_id_from_path(playbook_path.parent)
        missing_blocks = required_block_ids - available_block_ids
        if missing_blocks:
            msg: str = (
                "There are missing blocks that are part of this playbook, "
                "make sure they exist in the content-hub:\n"
                f"missing blocks: {', '.join(missing_blocks)}"
            )
            raise FatalValidationError(msg)
