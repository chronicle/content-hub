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

from typing import TYPE_CHECKING
from unittest import mock

import pytest

from mp.core.exceptions import NonFatalValidationError
from mp.core.unix import NonFatalCommandError
from mp.validate.pre_build_validation.integrations.release_notes_date_validation import (
    ReleaseNotesDateValidation,
)

if TYPE_CHECKING:
    from pathlib import Path

VALIDATOR = ReleaseNotesDateValidation()

VALID_RN = """\
- integration_version: '1.0'
  publish_time: '2024-01-01'
  description: Initial release
"""

INVALID_RN = """\
- integration_version: '1.0'
  publish_time: ''
  description: Initial release
"""

MISSING_PUBLISH_TIME_RN = """\
- integration_version: '1.0'
  description: Initial release
"""

TWO_ENTRY_RN_VALID = """\
- integration_version: '2.0'
  publish_time: '2026-04-28'
  description: New feature
- integration_version: '1.0'
  publish_time: '2024-01-01'
  description: Initial release
"""

TWO_ENTRY_RN_OLD_MISSING = """\
- integration_version: '2.0'
  publish_time: '2026-04-28'
  description: New feature
- integration_version: '1.0'
  description: Initial release
"""

OLD_MAIN_RN = """\
- integration_version: '1.0'
  description: Initial release
"""


class TestReleaseNotesDateValidationLocal:
    """Local mp validate runs (no GITHUB_PR_SHA) — all entries are checked."""

    def test_valid_date_passes(self, temp_integration: Path) -> None:
        rn = temp_integration / "release_notes.yaml"
        rn.write_text(VALID_RN, encoding="utf-8")
        VALIDATOR.run(temp_integration)  # no error

    def test_invalid_date_fails(self, temp_integration: Path) -> None:
        rn = temp_integration / "release_notes.yaml"
        rn.write_text(INVALID_RN, encoding="utf-8")
        with pytest.raises(NonFatalValidationError, match="invalid publish_time"):
            VALIDATOR.run(temp_integration)

    def test_missing_publish_time_fails(self, temp_integration: Path) -> None:
        rn = temp_integration / "release_notes.yaml"
        rn.write_text(MISSING_PUBLISH_TIME_RN, encoding="utf-8")
        with pytest.raises(NonFatalValidationError, match="invalid publish_time"):
            VALIDATOR.run(temp_integration)

    def test_no_release_notes_file_passes(self, temp_integration: Path) -> None:
        rn = temp_integration / "release_notes.yaml"
        rn.unlink(missing_ok=True)
        VALIDATOR.run(temp_integration)  # no error

    def test_old_entry_without_publish_time_fails_locally(self, temp_integration: Path) -> None:
        """In local runs, all entries (including pre-existing) are validated."""
        rn = temp_integration / "release_notes.yaml"
        rn.write_text(TWO_ENTRY_RN_OLD_MISSING, encoding="utf-8")
        with pytest.raises(NonFatalValidationError, match=r"v1:"):
            VALIDATOR.run(temp_integration)


class TestReleaseNotesDateValidationCI:
    """CI runs (GITHUB_PR_SHA set) — only new entries are checked."""

    def _make_changed(self, temp_integration: Path) -> list[Path]:
        return [temp_integration / "release_notes.yaml"]

    def test_new_valid_entry_passes(self, temp_integration: Path) -> None:
        rn = temp_integration / "release_notes.yaml"
        rn.write_text(TWO_ENTRY_RN_OLD_MISSING, encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=self._make_changed(temp_integration),
            ),
            mock.patch("mp.core.unix.get_file_content_from_main_branch", return_value=OLD_MAIN_RN),
        ):
            # v1.0 is pre-existing on main (no publish_time) — should be skipped
            # v2.0 is new and has a valid date — should pass
            VALIDATOR.run(temp_integration)

    def test_new_invalid_entry_fails(self, temp_integration: Path) -> None:
        rn = temp_integration / "release_notes.yaml"
        new_rn = """\
- integration_version: '2.0'
  publish_time: ''
  description: New feature
- integration_version: '1.0'
  publish_time: '2024-01-01'
  description: Initial release
"""
        rn.write_text(new_rn, encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=self._make_changed(temp_integration),
            ),
            mock.patch("mp.core.unix.get_file_content_from_main_branch", return_value=OLD_MAIN_RN),
            pytest.raises(NonFatalValidationError, match=r"v2:"),
        ):
            VALIDATOR.run(temp_integration)

    def test_no_changes_in_integration_skips(self, temp_integration: Path) -> None:
        rn = temp_integration / "release_notes.yaml"
        rn.write_text(INVALID_RN, encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch("mp.core.unix.get_files_unmerged_to_main_branch", return_value=[]),
        ):
            VALIDATOR.run(temp_integration)  # skipped entirely — no error

    def test_new_integration_not_on_main_all_entries_validated(self, temp_integration: Path) -> None:
        """When file doesn't exist on main, NonFatalCommandError is caught and all entries checked."""
        rn = temp_integration / "release_notes.yaml"
        rn.write_text(VALID_RN, encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=self._make_changed(temp_integration),
            ),
            mock.patch("mp.core.unix.get_file_content_from_main_branch", side_effect=NonFatalCommandError("not found")),
        ):
            VALIDATOR.run(temp_integration)  # valid date — passes

    def test_new_integration_not_on_main_invalid_date_fails(self, temp_integration: Path) -> None:
        rn = temp_integration / "release_notes.yaml"
        rn.write_text(INVALID_RN, encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=self._make_changed(temp_integration),
            ),
            mock.patch("mp.core.unix.get_file_content_from_main_branch", side_effect=NonFatalCommandError("not found")),
            pytest.raises(NonFatalValidationError, match="invalid publish_time"),
        ):
            VALIDATOR.run(temp_integration)

    def test_float_int_version_coercion_skips_correctly(self, temp_integration: Path) -> None:
        """YAML parses unquoted 1.0 as float and 1 as int — both must be treated as equal
        so a pre-existing entry with version 1.0 (float) is skipped when comparing to a
        new entry at version 2.0, and the old float-versioned entry isn't re-validated."""
        # Main branch has unquoted 1.0 → parsed as float by yaml.safe_load
        old_main_rn_unquoted = "- integration_version: 1.0\n  description: Initial\n"
        # Current file has new entry (2.0) plus pre-existing (1.0, no publish_time)
        current_rn = (
            "- integration_version: 2.0\n"
            "  publish_time: '2026-04-28'\n"
            "  description: New\n"
            "- integration_version: 1.0\n"
            "  description: Initial\n"
        )
        rn = temp_integration / "release_notes.yaml"
        rn.write_text(current_rn, encoding="utf-8")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=self._make_changed(temp_integration),
            ),
            mock.patch("mp.core.unix.get_file_content_from_main_branch", return_value=old_main_rn_unquoted),
        ):
            # v1.0 pre-exists on main (unquoted float); v2.0 is new with valid date → pass
            VALIDATOR.run(temp_integration)
