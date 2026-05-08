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

"""Tests for the SupportEmailValidation class."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest
import toml

from mp.core.exceptions import NonFatalValidationError
from mp.validate.validations.integrations.support_email_validation import (
    SupportEmailValidation,
)

if TYPE_CHECKING:
    from collections.abc import Iterator


def _write_pyproject(integration_path: Path, description: str) -> None:
    """Write a minimal pyproject.toml with the given description."""
    content = {
        "project": {
            "name": "mock_integration",
            "version": "1.0",
            "description": description,
        }
    }
    pyproject_path = integration_path / "pyproject.toml"
    with pyproject_path.open("w") as f:
        f.write(toml.dumps(content))


@pytest.fixture
def partner_integration(non_built_integration: Path) -> Iterator[Path]:
    """Create a temporary copy of the mock integration under a 'partner' parent directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        partner_dir = temp_root / "partner"
        partner_dir.mkdir()
        temp_path = partner_dir / non_built_integration.name
        shutil.copytree(non_built_integration.resolve(), temp_path)
        yield temp_path


class TestSupportEmailValidation:
    """Test suite for the SupportEmailValidation validator."""

    runner = SupportEmailValidation()

    def test_community_integration_skipped(self, temp_integration: Path) -> None:
        """Test that community integrations (not under 'partner') are skipped."""
        # temp_integration lives under 'third_party/mock_integration/', no 'partner' in parts
        # No email in description — should still pass because validator skips non-partner paths
        _write_pyproject(temp_integration, "No email here at all")
        self.runner.run(temp_integration)  # Should not raise

    def test_partner_with_valid_email_passes(self, partner_integration: Path) -> None:
        """Test that a partner integration with a valid support email passes."""
        _write_pyproject(partner_integration, "Support contact: support@example.com")
        self.runner.run(partner_integration)  # Should not raise

    def test_partner_missing_email_fails_in_ci(self, partner_integration: Path) -> None:
        """Test that a partner integration without an email fails when run in CI context."""
        _write_pyproject(partner_integration, "No email in this description")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[Path("some_file.py")],
            ),
            pytest.raises(NonFatalValidationError, match="support email"),
        ):
            self.runner.run(partner_integration)

    def test_partner_no_changes_in_ci_skips_validation(self, partner_integration: Path) -> None:
        """Test that a partner integration with no changed files in CI is skipped."""
        _write_pyproject(partner_integration, "No email in this description")

        with (
            mock.patch.dict("os.environ", {"GITHUB_PR_SHA": "abc123"}),
            mock.patch(
                "mp.core.unix.get_files_unmerged_to_main_branch",
                return_value=[],
            ),
        ):
            self.runner.run(partner_integration)  # Should not raise

    def test_partner_missing_email_fails_outside_ci(self, partner_integration: Path) -> None:
        """Test that a partner integration without an email fails when not in CI context."""
        _write_pyproject(partner_integration, "No email in this description")

        # No GITHUB_PR_SHA set — validator runs unconditionally for partner integrations
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            pytest.raises(NonFatalValidationError, match="support email"),
        ):
            self.runner.run(partner_integration)

    def test_partner_email_various_formats_pass(self, partner_integration: Path) -> None:
        """Test that various valid email formats in the description are accepted."""
        email_descriptions = [
            "Contact: user@domain.com",
            "Reach us at support.team@sub.example.org",
            "Email: foo-bar@baz.io for help",
        ]
        for description in email_descriptions:
            _write_pyproject(partner_integration, description)
            self.runner.run(partner_integration)  # Should not raise

    def test_partner_missing_pyproject_skips(self, partner_integration: Path) -> None:
        """Test that a missing pyproject.toml causes the validator to skip gracefully."""
        pyproject = partner_integration / "pyproject.toml"
        pyproject.unlink(missing_ok=True)
        self.runner.run(partner_integration)  # Should not raise
