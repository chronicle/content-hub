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

from typing import TYPE_CHECKING

from mp.core.data_models.playbooks.meta.display_info import PlaybookType
from mp.core.data_models.playbooks.meta.metadata import PlaybookMetadata

if TYPE_CHECKING:
    from pathlib import Path


def get_all_blocks_id_from_path(base_path: Path) -> set[str]:
    """Get all block identifiers from a directory of playbooks.

    Args:
        base_path: The path to the directory containing playbook directories.

    Returns:
        A set of all unique block identifiers found.

    """
    res: set[str] = set()

    for playbook in base_path.iterdir():
        if not playbook.is_dir():
            continue

        meta: PlaybookMetadata = PlaybookMetadata.from_non_built_path(playbook)
        if meta.type_ is PlaybookType.BLOCK:
            res.add(meta.identifier)

    return res
