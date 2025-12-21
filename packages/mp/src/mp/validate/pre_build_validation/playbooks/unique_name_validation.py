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

import mp.core.constants
import mp.core.file_utils
from mp.core.data_models.playbooks.meta.display_info import PlaybookDisplayInfo
from mp.core.exceptions import FatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, frozen=True)
class UniqueNameValidation:
    name: str = "Unique Name Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        display_name: str = mp.core.file_utils.open_display_info(
            playbook_path
        ).content_hub_display_name

        commercial_repo: Path = mp.core.file_utils.get_playbook_repository_base_path(
            mp.core.constants.COMMERCIAL_DIR_NAME
        )
        duplicate_paths: list[str] = _search_duplicate_names(display_name, commercial_repo)

        community_repo: Path = mp.core.file_utils.get_playbook_repository_base_path(
            mp.core.constants.COMMUNITY_DIR_NAME
        )
        duplicate_paths += _search_duplicate_names(display_name, community_repo)

        actual_duplicates = [
            path for path in duplicate_paths if Path(path).resolve() != playbook_path.resolve()
        ]

        if actual_duplicates:
            msg: str = (
                f"The playbook name '{display_name}' is already in use at the following locations: "
                f"{', '.join(actual_duplicates)}. "
                "Please use a unique name for your playbook before merging."
            )
            raise FatalValidationError(msg)


def _search_duplicate_names(display_name: str, playbook_repo: Path) -> list[str]:
    res: list[str] = []
    for playbook_dir in playbook_repo.iterdir():
        if not playbook_dir.is_dir():
            continue

        display_info: PlaybookDisplayInfo = mp.core.file_utils.open_display_info(playbook_dir)
        if display_name == display_info.content_hub_display_name:
            res.append(str(playbook_dir))

    return res
