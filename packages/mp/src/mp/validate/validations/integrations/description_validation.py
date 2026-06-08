# Copyright 2026 Google LLC
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

import dataclasses
import tomllib
from typing import TYPE_CHECKING

from mp.core import constants
from mp.core.exceptions import FatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class IntegrationDescriptionValidation:
    """Validate that the integration has a description in pyproject.toml."""

    name: str = "Integration Description Validation"

    @staticmethod
    def run(path: Path) -> None:
        """Check that the integration has a description in pyproject.toml.

        Args:
            path: The path of the integration to validate.

        Raises:
            FatalValidationError: If the description is missing or empty.

        """
        pyproject_path = path / constants.PROJECT_FILE
        if not pyproject_path.exists():
            # Structure validation should catch this, but we skip to avoid crash
            return

        try:
            with pyproject_path.open("rb") as f:
                data = tomllib.load(f)
        except Exception:
            # If we can't parse it, we skip and let other validations (or loader) fail
            return

        project = data.get("project", {})
        if "description" not in project:
            msg = f"Integration '{path.name}' is missing the 'description' field in {constants.PROJECT_FILE}."
            raise FatalValidationError(msg)

        description = project.get("description")
        if not isinstance(description, str) or not description.strip():
            msg = f"Integration '{path.name}' has an empty 'description' field in {constants.PROJECT_FILE}."
            raise FatalValidationError(msg)
