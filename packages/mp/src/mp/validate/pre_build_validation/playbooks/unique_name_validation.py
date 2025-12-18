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
from mp.core.data_models.playbooks.meta.display_info import PlaybookDisplayInfo
from mp.core.exceptions import FatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, frozen=True)
class UniqueNameValidation:
    name: str = "Unique Name Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        display_name: str = PlaybookDisplayInfo.from_non_built


def _search_duplicate_names(display_name: str, playbook_repo: Path) -> list[str]:
    pass
