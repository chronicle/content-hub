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

import mp.core.file_utils
from mp.core.data_models.playbooks.meta.metadata import PlaybookMetadata
from mp.core.data_models.playbooks.step.metadata import Step
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.playbooks.meta.display_info import PlaybookDisplayInfo


@dataclass(slots=True, frozen=True)
class DebugDataValidation:
    name: str = "Debug Data Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        """Check for inconsistencies in playbook debug data.

        Args:
            playbook_path: The path to the playbook directory.

        Raises:
            NonFatalValidationError: If any debug data inconsistencies are found.

        """
        display_info: PlaybookDisplayInfo = mp.core.file_utils.open_display_info(playbook_path)
        playbook_metadata: PlaybookMetadata = PlaybookMetadata.from_non_built_path(playbook_path)
        steps: list[Step] = Step.from_non_built_path(playbook_path)
        steps_with_debug_data: list[Step] = [step for step in steps if step.step_debug_data]

        if not steps_with_debug_data:
            return

        error_messages: list[str] = []

        if not display_info.allowed_debug_data:
            error_messages.append(
                "The playbook contains debug data, but 'allowed_debug_data' is set to False"
                " in the display info file. Set 'allowed_debug_data' to True to allow this data."
            )
            for step in steps_with_debug_data:
                error_messages.append(f"Step <{step.instance_name}> contains debug data.")  # noqa: PERF401

        if playbook_metadata.is_debug_mode:
            error_messages.append(
                "Playbook Simulator (definition.yaml/'is_debug_mode') cannot be "
                "enabled. Please disable it."
            )

        for step in steps_with_debug_data:
            if step.is_debug_mock_data:
                error_messages.append(  # noqa: PERF401
                    f"Step <{step.instance_name}> debug mode cannot be enabled. Please disable it."
                )

        if error_messages:
            raise NonFatalValidationError("\n".join(error_messages))
