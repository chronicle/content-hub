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

import mp.core.utils
from mp.core.data_models.playbooks.meta.display_info import PlaybookType
from mp.core.data_models.playbooks.meta.metadata import PlaybookMetadata
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, frozen=True)
class BlockEnvMatchesPlaybookEnvValidation:
    name: str = "Blocks Includes All Playbook Environments Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        """Validate that dependent blocks support all environments defined in the main playbook.

        Args:
            playbook_path: The path to the playbook directory.

        Raises:
            NonFatalValidationError: If a dependent block is missing environments
                required by the playbook.

        """
        dependent_blocks_ids: set[str] = mp.core.utils.get_playbook_dependent_blocks_ids(
            playbook_path
        )
        if not dependent_blocks_ids:
            return

        playbook_env: set[str] = set(
            PlaybookMetadata.from_non_built_path(playbook_path).environments
        )
        error_msg: list[str] = []
        for block in playbook_path.parent.iterdir():
            if not block.is_dir():
                continue

            block_def_file: PlaybookMetadata = PlaybookMetadata.from_non_built_path(block)

            if (
                block_def_file.type_ is not PlaybookType.BLOCK
                or block_def_file.identifier not in dependent_blocks_ids
            ):
                continue

            if missing := playbook_env.difference(set(block_def_file.environments)):
                error_msg.append(
                    f"Block <{block_def_file.name}> has missing environments from its playbook env"
                    f" {missing}"
                )

        if error_msg:
            raise NonFatalValidationError("\n,".join(error_msg))
