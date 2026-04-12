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
from typing import TYPE_CHECKING

import yaml

import mp.core.unix
from mp.core import constants
from mp.core.exceptions import NonFatalValidationError

if TYPE_CHECKING:
    from pathlib import Path


@dataclasses.dataclass(slots=True, frozen=True)
class ReleaseNotesDateValidation:
    """Validate that release notes have valid publish dates."""

    name: str = "Release Notes Date Validation"

    @staticmethod
    def run(validation_path: Path) -> None:
        """Check that all publish_time entries are valid YYYY-MM-DD dates.

        Args:
            validation_path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If any publish_time is invalid.

        """
        head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
        if head_sha:
            changed = mp.core.unix.get_files_unmerged_to_main_branch(
                "main", head_sha, validation_path
            )
            if not changed:
                return

        rn_path = validation_path / constants.RELEASE_NOTES_FILE
        if not rn_path.exists():
            return

        content = yaml.safe_load(rn_path.read_text(encoding="utf-8"))
        if not content or not isinstance(content, list):
            return

        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        invalid: list[str] = []
        for note in content:
            publish_time = str(note.get("publish_time", ""))
            if not date_pattern.match(publish_time):
                version = note.get("integration_version", "?")
                invalid.append(f"v{version}: '{publish_time}'")

        if invalid:
            entries = ", ".join(invalid)
            msg = f"Release notes have invalid publish_time values (expected YYYY-MM-DD): {entries}"
            raise NonFatalValidationError(msg)
