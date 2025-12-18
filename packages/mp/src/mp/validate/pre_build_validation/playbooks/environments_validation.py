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

from mp.core.constants import VALID_ENVIRONMENTS
from mp.core.data_models.playbooks.meta.metadata import PlaybookMetadata
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, frozen=True)
class EnvironmentsValidation:
    name: str = "Environments Validation"

    @staticmethod
    def run(playbook_path: Path) -> None:
        """Validate the environments of a playbook.

        Args:
            playbook_path: The path to the non-built playbook directory.

        Raises:
            NonFatalValidationError: If an invalid environment is found.

        """
        meta: PlaybookMetadata = PlaybookMetadata.from_non_built_path(playbook_path)
        invalid_environments = set(meta.environments).difference(VALID_ENVIRONMENTS)
        if invalid_environments:
            invalid_str = ", ".join(sorted(invalid_environments))
            valid_str = ", ".join(sorted(VALID_ENVIRONMENTS))
            msg = (
                f"Invalid environment(s) found: {invalid_str}. Valid environments are: {valid_str}."
            )
            raise NonFatalValidationError(msg)
