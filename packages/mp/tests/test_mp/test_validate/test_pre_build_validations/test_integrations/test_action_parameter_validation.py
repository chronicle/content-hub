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

"""Tests for the ActionParametersValuesValidation class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from mp.core import constants, file_utils
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.integrations.action_parameter_validation import (
    PARAMETERS_KEY,
    ActionParametersValuesValidation,
)

if TYPE_CHECKING:
    import pathlib


def _update_yaml_file(file_path: pathlib.Path, updates: dict[str, Any]) -> None:
    """Read a YAML file, update its content, and write it back."""
    content = file_utils.load_yaml_file(file_path)
    content.update(updates)
    file_utils.write_yaml_to_file(content, file_path)


class TestActionParameterValidation:
    """Test suite for the ActionParametersValuesValidation runner."""

    # Get an instance of the validator runner
    validator_runner = ActionParametersValuesValidation()

    def test_success_on_valid_integration(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration passes."""
        self.validator_runner.run(temp_integration)

    def test_success_on_action_without_parameters(self, temp_integration: pathlib.Path) -> None:
        """Test that an action with no 'parameter' key passes."""
        action_file = temp_integration / constants.ACTIONS_DIR / "ping.yaml"
        # Overwrite parameters with an empty list, which is valid
        _update_yaml_file(action_file, {PARAMETERS_KEY: []})
        self.validator_runner.run(temp_integration)

    @pytest.mark.parametrize("default_value", ["a", None, ""])
    def test_success_with_valid_optional_params(
        self,
        temp_integration: pathlib.Path,
        default_value: str | None,
    ) -> None:
        """Test valid params with optional_values and valid defaults."""
        action_file = temp_integration / constants.ACTIONS_DIR / "ping.yaml"
        params = [
            {
                "name": "valid_param",
                "type": "MULTI_CHOICE_PARAMETER",
                "optional_values": ["a", "b", "c"],
                "default_value": default_value,
            }
        ]
        _update_yaml_file(action_file, {PARAMETERS_KEY: params})
        self.validator_runner.run(temp_integration)

    def test_success_with_valid_non_optional_params(self, temp_integration: pathlib.Path) -> None:
        """Test that a string param with no optional_values passes."""
        action_file = temp_integration / constants.ACTIONS_DIR / "ping.yaml"
        params = [
            {
                "name": "valid_text",
                "type": "string",
                "optional_values": None,
                "default_value": "hello",
            },
            {
                "name": "valid_bool",
                "type": "boolean",
                # No optional_values key
                "default_value": True,
            },
        ]
        _update_yaml_file(action_file, {PARAMETERS_KEY: params})
        self.validator_runner.run(temp_integration)

    def test_success_with_empty_optional_values_list(self, temp_integration: pathlib.Path) -> None:
        action_file = temp_integration / constants.ACTIONS_DIR / "ping.yaml"
        params = [
            {
                "name": "empty_ddl",
                "type": "ddl",
                "optional_values": [],
                "default_value": None,
            }
        ]
        _update_yaml_file(action_file, {PARAMETERS_KEY: params})
        self.validator_runner.run(temp_integration)

    def test_failure_on_missing_optional_values(self, temp_integration: pathlib.Path) -> None:
        """Test failure when an optional type is missing optional_values."""
        action_file = temp_integration / constants.ACTIONS_DIR / "ping.yaml"
        params = [
            {
                "name": "invalid_param",
                "type": "MULTI_VALUES",
                "optional_values": None,
            }
        ]
        _update_yaml_file(action_file, {PARAMETERS_KEY: params})

        with pytest.raises(
            NonFatalValidationError,
            match="invalid_param from Ping",
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_extra_optional_values(self, temp_integration: pathlib.Path) -> None:
        """Test failure when a non-optional type (string) has optional_values."""
        action_file = temp_integration / constants.ACTIONS_DIR / "ping.yaml"
        params = [
            {
                "name": "invalid_param",
                "type": "string",
                "optional_values": ["a", "b"],
            }
        ]
        _update_yaml_file(action_file, {PARAMETERS_KEY: params})

        with pytest.raises(
            NonFatalValidationError,
            match="invalid_param from Ping",
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_default_value_not_in_options(self, temp_integration: pathlib.Path) -> None:
        """Test failure when default_value is not in optional_values."""
        action_file = temp_integration / constants.ACTIONS_DIR / "ping.yaml"
        params = [
            {
                "name": "invalid_default",
                "type": "ddl",
                "optional_values": ["a", "b"],
                "default_value": "c",
            }
        ]
        _update_yaml_file(action_file, {PARAMETERS_KEY: params})

        with pytest.raises(
            NonFatalValidationError,
            match="invalid_default from Ping",
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_default_value_and_non_optional_values_validations_failures(
        self, temp_integration: pathlib.Path
    ) -> None:
        """Test failure when both default_value check and the non-optional values check fail."""
        action_file = temp_integration / constants.ACTIONS_DIR / "ping.yaml"
        params = [
            {
                "name": "invalid_default",
                "type": "string",
                "optional_values": ["a", "b"],
                "default_value": "c",
            }
        ]
        _update_yaml_file(action_file, {PARAMETERS_KEY: params})

        with pytest.raises(NonFatalValidationError) as excinfo:
            self.validator_runner.run(temp_integration)

        assert str(excinfo.value).count("invalid_default from Ping") == 2

    def test_failure_on_case_sensitive_default_value(self, temp_integration: pathlib.Path) -> None:
        action_file = temp_integration / constants.ACTIONS_DIR / "ping.yaml"
        params = [
            {
                "name": "case_sensitive_param",
                "type": "ddl",
                "optional_values": ["Option1", "Option2"],
                "default_value": "option1",
            }
        ]
        _update_yaml_file(action_file, {PARAMETERS_KEY: params})

        with pytest.raises(
            NonFatalValidationError,
            match="case_sensitive_param from Ping",
        ):
            self.validator_runner.run(temp_integration)

    def test_failure_on_numeric_default_vs_string_options(
        self, temp_integration: pathlib.Path
    ) -> None:
        action_file = temp_integration / constants.ACTIONS_DIR / "ping.yaml"
        params = [
            {
                "name": "type_mismatch_param",
                "type": "ddl",
                "optional_values": ["1", "2", "3"],  # List of strings
                "default_value": 1,  # Integer
            }
        ]
        _update_yaml_file(action_file, {PARAMETERS_KEY: params})

        with pytest.raises(
            NonFatalValidationError,
            match="type_mismatch_param from Ping",
        ):
            self.validator_runner.run(temp_integration)
