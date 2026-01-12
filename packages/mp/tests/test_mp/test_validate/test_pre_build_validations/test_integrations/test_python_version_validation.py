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

"""Tests for the PythonVersionFileValidation runner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mp.core import constants
from mp.core.exceptions import FatalValidationError
from mp.validate.pre_build_validation.integrations.python_version_validation import (
    PythonVersionValidation,
)

if TYPE_CHECKING:
    import pathlib


def _remove_file(file_path: pathlib.Path) -> None:
    file_path.unlink(missing_ok=True)


class TestPythonVersionValidation:
    """Test suite for the PythonVersionValidation runner."""

    validator_runner = PythonVersionValidation()

    def test_success_on_valid_structure(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration structure passes."""
        self.validator_runner.run(temp_integration)

    def test_failure_on_missing_python_version_file(self, temp_integration: pathlib.Path) -> None:
        """Test failure when python version file is missing."""
        _remove_file(temp_integration / constants.PYTHON_VERSION_FILE)

        with pytest.raises(
            FatalValidationError,
            match=f"Integration is missing a `{constants.PYTHON_VERSION_FILE}` file.",
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_mismatched_python_version(self, temp_integration: pathlib.Path) -> None:
        """Test failure when python version in script does not match metadata."""
        python_version_file = temp_integration / constants.PYTHON_VERSION_FILE
        python_version_file.write_text("3.8")

        with pytest.raises(FatalValidationError, match="does not match the version in"):
            self.validator_runner.run(temp_integration)

    def test_failure_on_empty_python_version_file(self, temp_integration: pathlib.Path) -> None:
        """Test failure when python version is not specified in the script."""
        python_version_file = temp_integration / constants.PYTHON_VERSION_FILE
        python_version_file.write_text("")

        with pytest.raises(FatalValidationError, match="file is empty"):
            self.validator_runner.run(temp_integration)
