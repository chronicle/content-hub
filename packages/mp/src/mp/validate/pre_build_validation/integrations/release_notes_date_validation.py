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

        rn_path = validation_path / constants.RELEASE_NOTES_FILE
        if not rn_path.exists():
            return

        content = yaml.safe_load(rn_path.read_text(encoding="utf-8"))
        if not content or not isinstance(content, list):
            return

        # In PR context, only validate entries that are new (not present on main).
        # This avoids penalising pre-existing entries that predate the requirement.
        existing_versions: set[str] = set()
        if head_sha:
            changed = mp.core.unix.get_files_unmerged_to_main_branch("main", head_sha, validation_path)
            if not changed:
                return
            try:
                base_content = yaml.safe_load(mp.core.unix.get_file_content_from_main_branch(rn_path))
                if isinstance(base_content, list):
                    existing_versions = {str(note.get("integration_version", "")) for note in base_content}
            except mp.core.unix.NonFatalCommandError:
                pass  # File doesn't exist on main yet — all entries are new

        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        invalid: list[str] = []
        for note in content:
            version = str(note.get("integration_version", "?"))
            if head_sha and version in existing_versions:
                continue  # Pre-existing entry — skip
            publish_time = str(note.get("publish_time", ""))
            if not date_pattern.match(publish_time):
                invalid.append(f"v{version}: '{publish_time}'")

        if invalid:
            entries = ", ".join(invalid)
            msg = f"Release notes have invalid publish_time values (expected YYYY-MM-DD): {entries}"
            raise NonFatalValidationError(msg)
