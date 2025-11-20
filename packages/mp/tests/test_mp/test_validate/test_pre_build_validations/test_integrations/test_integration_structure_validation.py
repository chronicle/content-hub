# Copyright 2025 Google LLC
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

"""Tests for the IntegrationFileStructureValidation runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mp.core import constants
from mp.core.exceptions import FatalValidationError
from mp.validate.pre_build_validation.integrations.structure_validation import (
    IntegrationFileStructureValidation,
)

if TYPE_CHECKING:
    import pathlib


def _remove_file(file_path: pathlib.Path) -> None:
    file_path.unlink(missing_ok=True)


def _create_file(file_path: pathlib.Path, content: str = "") -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


class TestIntegrationFileStructureValidation:
    """Test suite for the IntegrationFileStructureValidation runner."""

    validator_runner = IntegrationFileStructureValidation()

    def test_success_on_valid_structure(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration structure passes."""
        self.validator_runner.run(temp_integration)

    def test_failure_on_missing_project_file(self, temp_integration: pathlib.Path) -> None:
        """Test failure when key file (pyproject.toml) is missing.

        This should cause `is_integration` to return False.
        """
        _remove_file(temp_integration / constants.PROJECT_FILE)

        with pytest.raises(FatalValidationError, match=r"missing essential pyproject\.toml file"):
            self.validator_runner.run(temp_integration)

        _create_file(temp_integration / constants.PROJECT_FILE)

    def test_failure_on_action_script_parity_error(self, temp_integration: pathlib.Path) -> None:
        """Test failure when a script file exists without a matching .yaml file.

        This should cause `is_integration` to raise a RuntimeError (from parity check).
        """
        # Create an extra script file without a .yaml
        _create_file(temp_integration / constants.ACTIONS_DIR / "extra_action.py")

        with pytest.raises(
            FatalValidationError, match=r"has a file 'extra_action\.py' without a  matching"
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_action_definition_parity_error(
        self, temp_integration: pathlib.Path
    ) -> None:
        """Test failure when a .yaml file exists without a matching script.

        This should also cause `is_integration` to raise a RuntimeError.
        """
        # Create an extra .yaml file without a script
        _create_file(temp_integration / constants.ACTIONS_DIR / "extra_action.yaml")

        with pytest.raises(
            FatalValidationError, match=r"has a file 'extra_action\.yaml' without a  matching"
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_job_script_parity_error(self, temp_integration: pathlib.Path) -> None:
        """Test failure when a script file exists without a matching .yaml file.

        This should cause `is_integration` to raise a RuntimeError (from parity check).
        """
        # Create an extra script file without a .yaml
        _create_file(temp_integration / constants.JOBS_DIR / "extra_job.py")

        with pytest.raises(
            FatalValidationError, match=r"has a file 'extra_job\.py' without a  matching"
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_job_definition_parity_error(self, temp_integration: pathlib.Path) -> None:
        """Test failure when a .yaml file exists without a matching script.

        This should also cause `is_integration` to raise a RuntimeError.
        """
        # Create an extra .yaml file without a script
        _create_file(temp_integration / constants.JOBS_DIR / "extra_job.yaml")

        with pytest.raises(
            FatalValidationError, match=r"has a file 'extra_job\.yaml' without a  matching"
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_connector_script_parity_error(self, temp_integration: pathlib.Path) -> None:
        """Test failure when a script file exists without a matching .yaml file.

        This should cause `is_integration` to raise a RuntimeError (from parity check).
        """
        # Create an extra script file without a .yaml
        _create_file(temp_integration / constants.CONNECTORS_DIR / "extra_connector.py")

        with pytest.raises(
            FatalValidationError, match=r"has a file 'extra_connector\.py' without a  matching"
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_connector_definition_parity_error(
        self, temp_integration: pathlib.Path
    ) -> None:
        """Test failure when a .yaml file exists without a matching script.

        This should also cause `is_integration` to raise a RuntimeError.
        """
        # Create an extra .yaml file without a script
        _create_file(temp_integration / constants.CONNECTORS_DIR / "extra_connector.yaml")

        with pytest.raises(
            FatalValidationError, match=r"has a file 'extra_connector\.yaml' without a  matching"
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_widget_script_parity_error(self, temp_integration: pathlib.Path) -> None:
        """Test failure when a script file exists without a matching .yaml file.

        This should cause `is_integration` to raise a RuntimeError (from parity check).
        """
        # Create an extra script file without a .yaml
        _create_file(temp_integration / constants.WIDGETS_DIR / "extra_widget.html")

        with pytest.raises(
            FatalValidationError, match=r"has a file 'extra_widget\.html' without a  matching"
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_widget_definition_parity_error(
        self, temp_integration: pathlib.Path
    ) -> None:
        """Test failure when a .yaml file exists without a matching script.

        This should also cause `is_integration` to raise a RuntimeError.
        """
        # Create an extra .yaml file without a script
        _create_file(temp_integration / constants.WIDGETS_DIR / "extra_widget.yaml")

        with pytest.raises(
            FatalValidationError, match=r"has a file 'extra_widget\.yaml' without a  matching"
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_invalid_parent_directory(self, temp_integration: pathlib.Path) -> None:
        """Test failure when the integration resides in an invalid parent directory."""
        invalid_parent_name = "invalid_integration_type_dir"

        # Move the valid temp_integration to a new path under this invalid parent
        invalid_parent_path = temp_integration.parent.parent / invalid_parent_name
        invalid_parent_path.mkdir(parents=True, exist_ok=True)

        new_integration_path = invalid_parent_path / temp_integration.name
        temp_integration.rename(new_integration_path)

        with pytest.raises(FatalValidationError, match="Integration is in an invalid dir"):
            self.validator_runner.run(new_integration_path)
