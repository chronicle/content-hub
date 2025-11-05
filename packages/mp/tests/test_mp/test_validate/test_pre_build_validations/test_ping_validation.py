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

"""Tests for the IntegrationHasPingActionValidation class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest

from mp.core import constants, file_utils
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.ping_validation import IntegrationHasPingActionValidation

if TYPE_CHECKING:
    import pathlib


def _remove_file(file_path: pathlib.Path) -> None:
    file_path.unlink(missing_ok=True)


def _update_yaml_file(file_path: pathlib.Path, updates: dict[str, Any]) -> None:
    """Read a YAML file, update its content, and write it back."""
    content = file_utils.load_yaml_file(file_path)
    content.update(updates)
    file_utils.write_yaml_to_file(content, file_path)


class TestPingValidation:
    """Test suite for the IntegrationHasPingActionValidation runner."""

    # Get an instance of the validator runner
    validator_runner = IntegrationHasPingActionValidation()

    def test_success_on_valid_integration_lower_case(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration (has a ping action) passes."""
        ping_def = temp_integration / constants.ACTIONS_DIR / f"ping{constants.DEF_FILE_SUFFIX}"
        _update_yaml_file(ping_def, {"name": "PING"})

        self.validator_runner.run(temp_integration)

    def test_success_on_valid_integration_upper_case(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration (has a ping action) passes."""
        self.validator_runner.run(temp_integration)

    def test_failure_on_missing_ping(self, temp_integration: pathlib.Path) -> None:
        """Test failure when the ping action is missing."""
        ping_def = temp_integration / constants.ACTIONS_DIR / f"ping{constants.DEF_FILE_SUFFIX}"
        ping_script = temp_integration / constants.ACTIONS_DIR / "ping.py"

        _remove_file(ping_script)
        _remove_file(ping_def)

        with pytest.raises(NonFatalValidationError, match="doesn't implement a 'ping' action"):
            self.validator_runner.run(temp_integration)

    def test_excluded_integrations_feature(self, temp_integration: pathlib.Path) -> None:
        """Test the excluded integrations feature works correctly."""
        ping_def = temp_integration / constants.ACTIONS_DIR / f"ping{constants.DEF_FILE_SUFFIX}"
        ping_script = temp_integration / constants.ACTIONS_DIR / "ping.py"

        _remove_file(ping_script)
        _remove_file(ping_def)

        with mock.patch.object(
            constants,
            "EXCLUDED_INTEGRATIONS_IDS_WITHOUT_PING",
            {"mock_integration"},
        ):
            self.validator_runner.run(temp_integration)
