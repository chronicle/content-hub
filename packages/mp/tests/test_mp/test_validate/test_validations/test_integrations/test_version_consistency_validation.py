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

"""Tests for the VersionConsistencyValidation class."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest
import toml
import yaml

from mp.core.exceptions import NonFatalValidationError
from mp.validate.validations.integrations.version_consistency_validation import (
    VersionConsistencyValidation,
)


def _write_pyproject_version(integration_path: Path, version: str) -> None:
    """Write a minimal pyproject.toml with the given version."""
    content = {
        "project": {
            "name": "mock_integration",
            "version": version,
            "description": "Mock integration",
        }
    }
    pyproject_path = integration_path / "pyproject.toml"
    with pyproject_path.open("w") as f:
        f.write(toml.dumps(content))


def _write_release_notes(integration_path: Path, versions: list[str]) -> None:
    """Write a release_notes.yaml with entries for the given versions."""
    entries = [
        {
            "version": v,
            "description": f"Release {v}",
            "publish_time": "2024-01-01",
            "item_name": "Integration Name",
            "item_type": "Integration",
            "new": i == 0,
            "regressive": False,
            "deprecated": False,
            "removed": False,
            "ticket_number": "TICKET-1",
        }
        for i, v in enumerate(versions)
    ]
    rn_path = integration_path / "release_notes.yaml"
    rn_path.write_text(yaml.dump(entries), encoding="utf-8")


class TestVersionConsistencyValidation:
    """Test suite for the VersionConsistencyValidation validator."""

    runner = VersionConsistencyValidation()

    def test_matching_versions_pass(self, temp_integration: Path) -> None:
        """Test that matching versions in pyproject.toml and release_notes.yaml pass."""
        _write_pyproject_version(temp_integration, "2.0")
        _write_release_notes(temp_integration, ["1.0", "2.0"])
        self.runner.run(temp_integration)  # Should not raise

    def test_mismatched_versions_fail(self, temp_integration: Path) -> None:
        """Test that mismatched versions raise NonFatalValidationError."""
        _write_pyproject_version(temp_integration, "3.0")
        _write_release_notes(temp_integration, ["1.0", "2.0"])

        with pytest.raises(NonFatalValidationError, match="doesn't match"):
            self.runner.run(temp_integration)

    def test_trailing_zero_normalization_passes(self, temp_integration: Path) -> None:
        """Test that '1.0' in pyproject.toml matches '1' in release_notes.yaml."""
        _write_pyproject_version(temp_integration, "1.0")
        _write_release_notes(temp_integration, ["1"])
        self.runner.run(temp_integration)  # Should not raise

    def test_trailing_zero_normalization_reversed_passes(self, temp_integration: Path) -> None:
        """Test that '1' in pyproject.toml matches '1.0' in release_notes.yaml."""
        _write_pyproject_version(temp_integration, "1")
        _write_release_notes(temp_integration, ["1.0"])
        self.runner.run(temp_integration)  # Should not raise

    def test_multiple_trailing_zeros_normalized(self, temp_integration: Path) -> None:
        """Test that '2.0.0' normalizes correctly to match '2'."""
        _write_pyproject_version(temp_integration, "2.0.0")
        _write_release_notes(temp_integration, ["2"])
        self.runner.run(temp_integration)  # Should not raise

    def test_missing_release_notes_skips_gracefully(self, temp_integration: Path) -> None:
        """Test that a missing release_notes.yaml causes the validator to skip."""
        _write_pyproject_version(temp_integration, "1.0")
        rn_path = temp_integration / "release_notes.yaml"
        rn_path.unlink(missing_ok=True)
        self.runner.run(temp_integration)  # Should not raise

    def test_missing_pyproject_skips_gracefully(self, temp_integration: Path) -> None:
        """Test that a missing pyproject.toml causes the validator to skip."""
        _write_release_notes(temp_integration, ["1.0"])
        pyproject_path = temp_integration / "pyproject.toml"
        pyproject_path.unlink(missing_ok=True)
        self.runner.run(temp_integration)  # Should not raise

    def test_no_changes_in_ci_skips_validation(self, temp_integration: Path) -> None:
        """Test that no changed files in CI causes the validator to skip."""
        _write_pyproject_version(temp_integration, "3.0")
        _write_release_notes(temp_integration, ["1.0", "2.0"])

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[],
            ),
        ):
            self.runner.run(temp_integration)  # Should not raise — no changes detected

    def test_mismatched_versions_detected_in_ci(self, temp_integration: Path) -> None:
        """Test that version mismatch is detected when changes exist in CI."""
        _write_pyproject_version(temp_integration, "3.0")
        _write_release_notes(temp_integration, ["1.0", "2.0"])

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[Path("some_file.py")],
            ),
            pytest.raises(NonFatalValidationError, match="doesn't match"),
        ):
            self.runner.run(temp_integration)

    def test_latest_release_note_is_used_for_comparison(self, temp_integration: Path) -> None:
        """Test that only the last entry in release_notes.yaml is compared."""
        # pyproject has 3.0, the LAST release note entry has 3.0 — should pass
        _write_pyproject_version(temp_integration, "3.0")
        _write_release_notes(temp_integration, ["1.0", "2.0", "3.0"])
        self.runner.run(temp_integration)  # Should not raise

    def test_empty_release_notes_skips_gracefully(self, temp_integration: Path) -> None:
        """Test that an empty release_notes.yaml causes the validator to skip."""
        _write_pyproject_version(temp_integration, "1.0")
        rn_path = temp_integration / "release_notes.yaml"
        rn_path.write_text("", encoding="utf-8")
        self.runner.run(temp_integration)  # Should not raise

    def test_pyproject_matches_non_last_entry_fails(self, temp_integration: Path) -> None:
        """Only the last RN entry is compared; matching an earlier entry is not sufficient."""
        # pyproject=2.0 matches the middle entry but NOT the last (3.0) — should fail
        _write_pyproject_version(temp_integration, "2.0")
        _write_release_notes(temp_integration, ["1.0", "2.0", "3.0"])

        with pytest.raises(NonFatalValidationError, match="doesn't match"):
            self.runner.run(temp_integration)
