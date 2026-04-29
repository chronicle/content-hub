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


def _normalize_version(v: object) -> str:
    """Normalize a YAML-parsed version value to a canonical string.

    YAML parses unquoted ``1.0`` as ``float`` and ``1`` as ``int``, causing
    ``str(1.0) == "1.0"`` while ``str(1) == "1"``.  Converting through
    ``float`` first ensures both map to the same representation.

    Returns:
        A canonical string representation of the version.

    """
    try:
        f = float(str(v))
        if f == int(f):
            return str(int(f))
        return str(f)
    except (ValueError, OverflowError, TypeError):
        return str(v)


def _versions_on_main(rn_path: Path) -> set[str]:
    """Return normalized version strings from the main-branch release notes.

    Args:
        rn_path: Path to the release_notes.yaml file in the working tree.

    Returns:
        Set of canonical version strings already on main, or an empty set
        when the file does not yet exist on main or cannot be parsed.

    """
    try:
        base_content = yaml.safe_load(mp.core.unix.get_file_content_from_main_branch(rn_path))
        if isinstance(base_content, list):
            return {_normalize_version(note.get("integration_version", "")) for note in base_content}
    except mp.core.unix.NonFatalCommandError:
        pass  # File doesn't exist on main — new integration, validate all entries
    return set()


@dataclasses.dataclass(slots=True, frozen=True)
class ReleaseNotesDateValidation:
    """Validate that release notes have valid publish dates."""

    name: str = "Release Notes Date Validation"

    @staticmethod
    def run(path: Path) -> None:
        """Check that all publish_time entries are valid YYYY-MM-DD dates.

        Args:
            path: The path of the integration to validate.

        Raises:
            NonFatalValidationError: If any publish_time is invalid.

        """
        head_sha: str | None = os.environ.get("GITHUB_PR_SHA")
        if head_sha:
            changed = mp.core.unix.get_files_unmerged_to_main_branch("main", head_sha, path)
            if not changed:
                return

        rn_path = path / constants.RELEASE_NOTES_FILE
        if not rn_path.exists():
            return

        content = yaml.safe_load(rn_path.read_text(encoding="utf-8"))
        if not content or not isinstance(content, list):
            return

        # In PR context, only validate entries that are new (not present on main).
        # This avoids penalising pre-existing entries that predate the requirement.
        existing_versions: set[str] = set()
        if head_sha:
            if not mp.core.unix.get_files_unmerged_to_main_branch("main", head_sha, validation_path):
                return
            existing_versions = _versions_on_main(rn_path)

        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        invalid: list[str] = []
        for note in content:
            version = _normalize_version(note.get("integration_version", "?"))
            if head_sha and version in existing_versions:
                continue  # Pre-existing entry — skip
            publish_time = str(note.get("publish_time", ""))
            if not date_pattern.match(publish_time):
                invalid.append(f"v{version}: '{publish_time}'")

        if invalid:
            entries = ", ".join(invalid)
            msg = f"Release notes have invalid publish_time values (expected YYYY-MM-DD): {entries}"
            raise NonFatalValidationError(msg)
