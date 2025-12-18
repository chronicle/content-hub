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

        steps: list[Step] = Step.from_non_built_path(playbook_path)
        error_messages: list[str] = []
        has_debug_data = False

        for step in steps:
            if step.step_debug_data:
                has_debug_data = True
                if not step.is_debug_mock_data:
                    error_messages.append(
                        f"Step <{step.instance_name}> has debug data but flag "
                        f"'is_debug_mock_data' is False."
                    )

        if has_debug_data and not display_info.allowed_debug_data:
            error_messages.append(
                "Playbook contains debug data but the field 'allowed_debug_data' in "
                "the display info is set to False, to allow debug data mark "
                "it True."
            )

        if error_messages:
            raise NonFatalValidationError("\n".join(error_messages))
