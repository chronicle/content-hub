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
import os
import re
import tomllib
from typing import TYPE_CHECKING

import mp.core.unix
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class SupportEmailValidation:
    """Validate that partner integrations include a support email."""

    name: str = "Support Email Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Check that partner integrations have a support email in pyproject.toml.

        Only applies to integrations under third_party/partner/.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If a partner integration is missing a
                support email in its pyproject.toml description.

        """
        if "partner" not in validation_path.parts:
            return

        head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
        if head_sha:
            changed = mp.core.unix.get_files_unmerged_to_main_branch(
                "main", head_sha, validation_path
            )
            if not changed:
                return

        pyproject = validation_path / "pyproject.toml"
        if not pyproject.exists():
            return

        with pyproject.open("rb") as f:
            data = tomllib.load(f)

        description = data.get("project", {}).get("description", "")
        if not re.search(r"[\w.-]+@[\w.-]+\.\w+", description):
            msg = (
                f"Partner integration '{validation_path.name}' must include a "
                f"support email in pyproject.toml description"
            )
            raise NonFatalValidationError(msg)
