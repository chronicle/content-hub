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

from mp.core.data_models.playbooks.overview.metadata import Overview
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


ALLOWED_ROLES: set[str] = {"Administrator", "Tier1", "Tier2", "Tier3", "SocManager", "CISO"}


@dataclass(slots=True, frozen=True)
class RolesValidation:
    name: str = "Roles Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        """Validate playbook roles in the overviews section.

        Args:
            playbook_path: The path to the playbook directory.

        Raises:
            NonFatalValidationError: If invalid roles are found in playbook overviews.

        """
        overviews: list[Overview] = Overview.from_non_built_path(playbook_path)
        for ov in overviews:
            if invalid_roles := set(ov.role_names).difference(ALLOWED_ROLES):
                msg: str = (
                    f"Found invalid roles in playbook overviews: {', '.join(invalid_roles)}."
                    f" Only the following roles are allowed: {', '.join(ALLOWED_ROLES)}"
                )
                raise NonFatalValidationError(msg)
