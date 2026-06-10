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

from typing import TYPE_CHECKING

import pytest
import toml
import yaml

from mp.core.exceptions import FatalValidationError
from mp.validate.validations.integrations.description_validation import (
    IntegrationDescriptionValidation,
)

if TYPE_CHECKING:
    from pathlib import Path


def _write_pyproject(integration_path: Path, content: dict) -> None:
    """Write a pyproject.toml with the given content."""
    pyproject_path = integration_path / "pyproject.toml"
    with pyproject_path.open("w") as f:
        f.write(toml.dumps(content))


def _write_action_yaml(integration_path: Path, action_name: str, content: dict) -> None:
    """Write an action YAML file with the given content."""
    actions_dir = integration_path / "actions"
    actions_dir.mkdir(parents=True, exist_ok=True)
    action_path = actions_dir / f"{action_name}.yaml"
    with action_path.open("w", encoding="utf-8") as f:
        yaml.dump(content, f)


class TestIntegrationDescriptionValidation:
    """Test suite for the IntegrationDescriptionValidation validator."""

    runner = IntegrationDescriptionValidation()

    # --- Integration Level Tests ---

    def test_valid_description_passes(self, temp_integration: Path) -> None:
        """Test that a valid integration description passes validation."""
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
        with pytest.raises(FatalValidationError, match="Integration is missing the 'description' field in pyproject.toml."):
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
        with pytest.raises(FatalValidationError, match="Integration has an empty 'description' field in pyproject.toml."):
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
        with pytest.raises(FatalValidationError, match="Integration has an empty 'description' field in pyproject.toml."):
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
        with pytest.raises(FatalValidationError, match="Integration has an empty 'description' field in pyproject.toml."):
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

    def test_missing_project_section_fails(self, temp_integration: Path) -> None:
        """Test that missing project section fails validation."""
        content = {
            "not_project": {
                "name": "mock_integration",
            },
        }
        _write_pyproject(temp_integration, content)
        with pytest.raises(FatalValidationError, match="Integration is missing the 'project' section in pyproject.toml."):
            self.runner.run(temp_integration)

    def test_non_dict_project_section_fails(self, temp_integration: Path) -> None:
        """Test that non-dict project section fails validation."""
        content = {
            "project": "not a dict"
        }
        _write_pyproject(temp_integration, content)
        with pytest.raises(FatalValidationError, match="Integration is missing the 'project' section in pyproject.toml."):
            self.runner.run(temp_integration)

    def test_valid_integration_and_actions_passes(self, temp_integration: Path) -> None:
        """Test that a valid integration and valid actions pass validation."""
        pyproject_content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
                "description": "Valid integration description.",
            },
        }
        _write_pyproject(temp_integration, pyproject_content)

        action_content = {
            "name": "My Action",
            "description": "Action description",
            "parameters": [
                {
                    "name": "Param1",
                    "description": "Parameter 1 description",
                }
            ],
        }
        _write_action_yaml(temp_integration, "my_action", action_content)

        self.runner.run(temp_integration)  # Should not raise

    def test_action_with_no_parameters_passes(self, temp_integration: Path) -> None:
        """Test that an action with empty or missing parameters passes."""
        pyproject_content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
                "description": "Valid integration description.",
            },
        }
        _write_pyproject(temp_integration, pyproject_content)

        action_content_empty = {
            "name": "Ping",
            "parameters": [],
        }
        _write_action_yaml(temp_integration, "ping", action_content_empty)

        action_content_missing = {
            "name": "NoParams",
        }
        _write_action_yaml(temp_integration, "no_params", action_content_missing)

        self.runner.run(temp_integration)  # Should not raise

    def test_missing_action_parameter_description_fails(self, temp_integration: Path) -> None:
        """Test that a missing parameter description fails validation."""
        pyproject_content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
                "description": "Valid integration description.",
            },
        }
        _write_pyproject(temp_integration, pyproject_content)

        action_content = {
            "name": "My Action",
            "parameters": [
                {
                    "name": "Param1",
                }
            ],
        }
        _write_action_yaml(temp_integration, "my_action", action_content)

        msg = "Action 'my_action' parameter 'Param1' is missing 'description' field."
        with pytest.raises(FatalValidationError, match=msg):
            self.runner.run(temp_integration)

    def test_empty_action_parameter_description_fails(self, temp_integration: Path) -> None:
        """Test that an empty parameter description fails validation."""
        pyproject_content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
                "description": "Valid integration description.",
            },
        }
        _write_pyproject(temp_integration, pyproject_content)

        action_content = {
            "name": "My Action",
            "parameters": [
                {
                    "name": "Param1",
                    "description": "   ",
                }
            ],
        }
        _write_action_yaml(temp_integration, "my_action", action_content)

        msg = "Action 'my_action' parameter 'Param1' has an empty 'description' field."
        with pytest.raises(FatalValidationError, match=msg):
            self.runner.run(temp_integration)

    def test_multiple_errors_accumulated(self, temp_integration: Path) -> None:
        """Test that multiple errors are accumulated and reported together."""
        pyproject_content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
            },
        }
        _write_pyproject(temp_integration, pyproject_content)

        action_content = {
            "name": "My Action",
            "parameters": [
                {
                    "name": "Param1",
                }
            ],
        }
        _write_action_yaml(temp_integration, "my_action", action_content)

        with pytest.raises(FatalValidationError) as exc_info:
            self.runner.run(temp_integration)

        err_msg = str(exc_info.value)
        assert "Integration is missing the 'description' field in pyproject.toml." in err_msg
        assert "Action 'my_action' parameter 'Param1' is missing 'description' field." in err_msg

    def test_invalid_action_yaml_skipped(self, temp_integration: Path) -> None:
        """Test that invalid action YAML files are skipped gracefully."""
        pyproject_content = {
            "project": {
                "name": "mock_integration",
                "version": "1.0",
                "description": "Valid integration description.",
            },
        }
        _write_pyproject(temp_integration, pyproject_content)

        actions_dir = temp_integration / "actions"
        actions_dir.mkdir(parents=True, exist_ok=True)
        action_path = actions_dir / "invalid_action.yaml"
        action_path.write_text("invalid: [yaml: block")

        self.runner.run(temp_integration)  # Should not raise
