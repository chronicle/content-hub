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

"""Tests for the NoDisabledComponentsInIntegrationValidation class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

import mp.core.constants
from mp.core import file_utils
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.disabled_validation import (
    NoDisabledComponentsInIntegrationValidation,
)

if TYPE_CHECKING:
    import pathlib


def _update_yaml_file(file_path: pathlib.Path, updates: dict[str, Any]) -> None:
    """Read a YAML file, update its content, and write it back."""
    content = file_utils.load_yaml_file(file_path)
    content.update(updates)
    file_utils.write_yaml_to_file(content, file_path)


class TestDisabledValidation:
    """Test suite for the NoDisabledComponentsInIntegrationValidation runner."""

    # Get an instance of the validator runner
    validator_runner = NoDisabledComponentsInIntegrationValidation()

    def test_success_on_valid_integration(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration (no disabled flags) passes."""
        self.validator_runner.run(temp_integration)

    def test_failure_on_disabled_action_flag(self, temp_integration: pathlib.Path) -> None:
        """Test failure when an action's 'is_enable' flag is false."""
        ping_def_file = (
            temp_integration
            / mp.core.constants.ACTIONS_DIR
            / f"ping{mp.core.constants.DEF_FILE_SUFFIX}"
        )
        _update_yaml_file(ping_def_file, {"is_enabled": False})

        with pytest.raises(NonFatalValidationError, match="Disabled actions: Ping"):
            self.validator_runner.run(temp_integration)

    def test_failure_on_disabled_connector_flag(self, temp_integration: pathlib.Path) -> None:
        """Test failure when a connector's 'is_enable' flag is false."""
        connector_def_file = (
            temp_integration
            / mp.core.constants.CONNECTORS_DIR
            / f"connector{mp.core.constants.DEF_FILE_SUFFIX}"
        )
        _update_yaml_file(connector_def_file, {"is_enabled": False})

        with pytest.raises(
            NonFatalValidationError, match="Disabled connectors: Mock Integration Connector"
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_disabled_job_flag(self, temp_integration: pathlib.Path) -> None:
        """Test failure when a job's 'is_enable' flag is false."""
        job_def_file = (
            temp_integration
            / mp.core.constants.JOBS_DIR
            / f"job{mp.core.constants.DEF_FILE_SUFFIX}"
        )
        _update_yaml_file(job_def_file, {"is_enabled": False})

        with pytest.raises(NonFatalValidationError, match="Disabled jobs: Mock Integration Job"):
            self.validator_runner.run(temp_integration)
