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

from pydantic import dataclasses

from mp.core.data_models.playbooks.meta.display_info import PlaybookType
from mp.core.data_models.playbooks.playbook import Playbook
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class BlockDoesNotContainAnOverviewValidation:
    name: str = "Block Overview Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        """Validate that blocks do not contain overviews.

        Args:
             playbook_path: The path to the playbook.

        Raises:
            NonFatalValidationError: If the playbook contains overviews.

        """
        playbook: Playbook = Playbook.from_non_built_path(playbook_path)
        if playbook.meta_data.type_ is PlaybookType.BLOCK and playbook.overviews:
            msg: str = "Block cannot have overviews"
            raise NonFatalValidationError(msg)
