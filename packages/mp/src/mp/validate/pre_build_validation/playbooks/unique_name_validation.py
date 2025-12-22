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
from mp.core.exceptions import FatalValidationError

if TYPE_CHECKING:
    from pathlib import Path

    from mp.core.data_models.playbooks.meta.display_info import PlaybookDisplayInfo


@dataclass(slots=True, frozen=True)
class UniqueNameValidation:
    name: str = "Unique Name Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        """Validate that a playbook's display name is unique.

        Args:
            playbook_path: The path to the playbook to validate.

        Raises:
            FatalValidationError: If a playbook with the same display name
                already exists.

        """
        display_name: str = mp.core.file_utils.get_display_info(
            playbook_path
        ).content_hub_display_name

        duplicate_paths: set[Path] = set()
        for repo in mp.core.constants.PLAYBOOK_REPOSITORY_TYPE:
            repo_path: Path = mp.core.file_utils.get_playbook_repository_base_path(repo)
            duplicate_paths.update(_search_duplicate_names(display_name, repo_path))

        duplicate_paths.discard(playbook_path)

        if duplicate_paths:
            msg: str = (
                f"The playbook display name '{display_name}' is already in use at the following "
                f"locations: {', '.join(str(p) for p in duplicate_paths)}. "
                "Please use a unique name for your playbook before merging."
            )
            raise FatalValidationError(msg)


def _search_duplicate_names(display_name: str, playbook_repo: Path) -> set[Path]:
    res: set[Path] = set()
    for playbook_dir in playbook_repo.iterdir():
        if not playbook_dir.is_dir():
            continue
        try:
            display_info: PlaybookDisplayInfo = mp.core.file_utils.get_display_info(playbook_dir)
            if display_name == display_info.content_hub_display_name:
                res.add(playbook_dir)
        except FileNotFoundError:
            continue

    return res
