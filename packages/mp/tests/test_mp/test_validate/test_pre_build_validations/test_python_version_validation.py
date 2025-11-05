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

"""Tests for the PythonVersionFileValidation class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from mp.core import constants, file_utils
from mp.core.data_models.integration_meta.metadata import PythonVersion
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation import PythonVersionFileValidation

if TYPE_CHECKING:
    import pathlib


def _write_python_version_file(integration_path: pathlib.Path, content: str) -> None:
    file_path = integration_path / constants.PYTHON_VERSION_FILE
    file_path.write_text(content, encoding="utf-8")


def _update_yaml_file(file_path: pathlib.Path, updates: dict[str, Any]) -> None:
    """Read a YAML file, update its content, and write it back."""
    content = file_utils.load_yaml_file(file_path)
    content.update(updates)
    file_utils.write_yaml_to_file(content, file_path)


class TestPythonVersionValidation:
    """Test suite for the PythonVersionFileValidation runner."""

    # Get an instance of the validator runner
    validator_runner = PythonVersionFileValidation()

    def test_success_on_valid_integration_no_python_version_in_metadata(
        self, temp_integration: pathlib.Path
    ) -> None:
        """Test that a valid integration (has a '.python-version' file and no python_version
        key in metadata) passes."""
        _write_python_version_file(temp_integration, PythonVersion.PY_3_11.to_string())
        self.validator_runner.run(temp_integration)

    def test_success_on_valid_integration_matching_python_version_in_metadata(
        self, temp_integration: pathlib.Path
    ) -> None:
        """Test that a valid integration (has a '.python-version' file and a matching
        python_version key in metadata) passes."""
        _write_python_version_file(temp_integration, PythonVersion.PY_3_11.to_string())
        _update_yaml_file(
            temp_integration / constants.DEFINITION_FILE,
            {"python_version": PythonVersion.PY_3_11.to_string()},
        )

        self.validator_runner.run(temp_integration)

    def test_failure_on_missing_python_version_file(self, temp_integration: pathlib.Path) -> None:
        """Test that an integration with a missing '.python-version' file fails."""
        with pytest.raises(
            NonFatalValidationError, match=f"Missing {constants.PYTHON_VERSION_FILE} file"
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_unmatching_python_version_in_metadata(
        self, temp_integration: pathlib.Path
    ) -> None:
        """Test that an invalid integration (has a '.python-version' file and an unmatching
        python_version key in metadata) fails."""
        _write_python_version_file(temp_integration, "3.1")
        _update_yaml_file(
            temp_integration / constants.DEFINITION_FILE,
            {"python_version": PythonVersion.PY_3_11.to_string()},
        )

        with pytest.raises(NonFatalValidationError, match="Make sure the version in the"):
            self.validator_runner.run(temp_integration)
