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
from mp.core.data_models.playbooks.meta.metadata import PlaybookMetadata

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, frozen=True)
class BlockIncludesAllEnvironmentsValidation:
    name: str = "Blocks Includes All Playbook Environments Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        dependent_blocks_ids: set[str] = mp.core.utils.get_playbook_dependent_blocks_ids(
            playbook_path
        )
        def_file: PlaybookMetadata = PlaybookMetadata.from_non_built_path(playbook_path)
