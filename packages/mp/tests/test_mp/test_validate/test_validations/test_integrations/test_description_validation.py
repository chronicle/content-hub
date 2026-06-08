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

"""Tests for the IntegrationDescriptionValidation class."""

from __future__ import annotations

from pathlib import Path
import pytest
import toml

from mp.core.exceptions import FatalValidationError
from mp.validate.validations.integrations.description_validation import (
    IntegrationDescriptionValidation,
)


def _write_pyproject(integration_path: Path, content: dict) -> None:
    """Write a pyproject.toml with the given content."""
    pyproject_path = integration_path / "pyproject.toml"
    with pyproject_path.open("w") as f:
        f.write(toml.dumps(content))


class TestIntegrationDescriptionValidation:
    """Test suite for the IntegrationDescriptionValidation validator."""

    runner = IntegrationDescriptionValidation()

    def test_valid_description_passes(self, temp_integration: Path) -> None:
        """Test that a valid description passes validation."""
        content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
                "description": "This is a valid description of the integration.",
            },
        }
        _write_pyproject(temp_integration, content)
        self.runner.run(temp_integration)  # Should not raise

    def test_missing_description_fails(self, temp_integration: Path) -> None:
        """Test that missing description field fails validation."""
        content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
            },
        }
        _write_pyproject(temp_integration, content)
        with pytest.raises(FatalValidationError, match="missing the 'description' field"):
            self.runner.run(temp_integration)

    def test_empty_description_fails(self, temp_integration: Path) -> None:
        """Test that empty description field fails validation."""
        content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
                "description": "",
            },
        }
        _write_pyproject(temp_integration, content)
        with pytest.raises(FatalValidationError, match="has an empty 'description' field"):
            self.runner.run(temp_integration)

    def test_whitespace_description_fails(self, temp_integration: Path) -> None:
        """Test that description containing only whitespace fails validation."""
        content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
                "description": "   ",
            },
        }
        _write_pyproject(temp_integration, content)
        with pytest.raises(FatalValidationError, match="has an empty 'description' field"):
            self.runner.run(temp_integration)

    def test_non_string_description_fails(self, temp_integration: Path) -> None:
        """Test that non-string description field fails validation."""
        content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
                "description": 12345,
            },
        }
        _write_pyproject(temp_integration, content)
        with pytest.raises(FatalValidationError, match="has an empty 'description' field"):
            self.runner.run(temp_integration)

    def test_missing_pyproject_skips(self, temp_integration: Path) -> None:
        """Test that missing pyproject.toml skips validation gracefully."""
        pyproject = temp_integration / "pyproject.toml"
        pyproject.unlink(missing_ok=True)
        self.runner.run(temp_integration)  # Should not raise

    def test_invalid_toml_skips(self, temp_integration: Path) -> None:
        """Test that invalid TOML skips validation gracefully."""
        pyproject = temp_integration / "pyproject.toml"
        pyproject.write_text("invalid = [toml")
        self.runner.run(temp_integration)  # Should not raise
