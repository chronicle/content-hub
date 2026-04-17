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
from typing import TYPE_CHECKING

import mp.core.unix
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path

# Directories where __init__.py must be empty (only license headers allowed)
_CHECKED_DIRS = ("actions", "core", "connectors", "jobs")


@dataclasses.dataclass(slots=True, frozen=True)
class EmptyInitFilesValidation:
    """Validate that __init__.py files in source directories are empty."""

    name: str = "Empty Init Files Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Check that __init__.py files in actions/, core/, etc. are empty.

        License headers and comments are allowed. Only actual Python code
        is flagged.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If an __init__.py contains code.

        """
        head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
        if head_sha:
            changed = mp.core.unix.get_files_unmerged_to_main_branch(
                "main", head_sha, validation_path
            )
            if not changed:
                return

        non_empty: list[str] = []

        for dir_name in _CHECKED_DIRS:
            init_file = validation_path / dir_name / "__init__.py"
            if not init_file.exists():
                continue

            content = init_file.read_text(encoding="utf-8").strip()
            # Filter out license headers, empty lines, and future imports
            code_lines = [
                line
                for line in content.splitlines()
                if line.strip()
                and not line.strip().startswith("#")
                and not line.strip().startswith("from __future__")
            ]

            if code_lines:
                non_empty.append(f"{dir_name}/__init__.py")

        if non_empty:
            files = ", ".join(non_empty)
            msg = f"__init__.py files must be empty (only license headers allowed): {files}"
            raise NonFatalValidationError(msg)
