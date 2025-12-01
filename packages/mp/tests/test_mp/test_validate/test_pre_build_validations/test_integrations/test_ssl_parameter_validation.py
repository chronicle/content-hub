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

"""Tests for the SslParameterExistsValidation class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest

from mp.core import constants, file_utils
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.integrations.connectors_ssl_validation import (
    SslParameterExistsInConnectorsValidation,
)
from mp.validate.pre_build_validation.integrations.integration_ssl_validation import (
    SslParameterExistsInIntegrationValidation,
)

if TYPE_CHECKING:
    import pathlib


def _update_yaml_file(file_path: pathlib.Path, updates: dict[str, Any]) -> None:
    """Read a YAML file, update its content, and write it back."""
    content = file_utils.load_yaml_file(file_path)
    content.update(updates)
    file_utils.write_yaml_to_file(content, file_path)


class TestSSLParameterValidation:
    """Test suite for the SslParameterExistsInIntegrationValidation runner."""

    integration_runner = SslParameterExistsInIntegrationValidation()
    connectors_runner = SslParameterExistsInConnectorsValidation()

    def test_success_on_valid_integration(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration passes."""
        self.integration_runner.run(temp_integration)
        self.connectors_runner.run(temp_integration)

    def test_ssl_parameter_missing_in_integration(self, temp_integration: pathlib.Path) -> None:
        """Test failure when 'Verify SSL' is missing from the integration."""
        integration_file = temp_integration / constants.DEFINITION_FILE
        _update_yaml_file(integration_file, {"parameters": []})

        with pytest.raises(NonFatalValidationError, match="missing a 'Verify SSL' parameter"):
            self.integration_runner.run(temp_integration)

    def test_ssl_parameter_missing_in_connector(self, temp_integration: pathlib.Path) -> None:
        """Test failure when 'Verify SSL' is missing from a connector."""
        connector_file = temp_integration / constants.CONNECTORS_DIR / "connector.yaml"
        _update_yaml_file(connector_file, {"parameters": []})

        with pytest.raises(NonFatalValidationError, match="missing a 'Verify SSL' parameter"):
            self.connectors_runner.run(temp_integration)

    def test_ssl_parameter_excluded_integration(self, temp_integration: pathlib.Path) -> None:
        """Test that an excluded integration passes without SSL validation."""

        integration_file = temp_integration / constants.DEFINITION_FILE
        _update_yaml_file(integration_file, {"parameters": []})
        with mock.patch.object(
            constants,
            "EXCLUDED_NAMES_WITHOUT_VERIFY_SSL",
            {"Mock Integration"},
        ):
            self.integration_runner.run(temp_integration)

    def test_ssl_parameter_wrong_type(self, temp_integration: pathlib.Path) -> None:
        """Test failure when 'Verify SSL' has the wrong type."""
        integration_file = temp_integration / constants.DEFINITION_FILE
        params = [
            {
                "name": "Verify SSL",
                "type": "string",
            }
        ]
        _update_yaml_file(integration_file, {"parameters": params})

        with pytest.raises(NonFatalValidationError, match="must be of type 'boolean'"):
            self.integration_runner.run(temp_integration)

    def test_ssl_parameter_wrong_default_value(self, temp_integration: pathlib.Path) -> None:
        """Test failure when 'Verify SSL' has the wrong default value."""
        integration_file = temp_integration / constants.DEFINITION_FILE
        params = [
            {
                "name": "Verify SSL",
                "type": "boolean",
                "default_value": False,
            }
        ]
        _update_yaml_file(integration_file, {"parameters": params})

        with pytest.raises(NonFatalValidationError, match="must be a boolean true"):
            self.integration_runner.run(temp_integration)

    def test_ssl_parameter_excluded_from_default_value_check(
        self, temp_integration: pathlib.Path
    ) -> None:
        """Test that an excluded integration can have SSL default as False."""
        integration_file = temp_integration / constants.DEFINITION_FILE
        params = [
            {
                "name": "Verify SSL",
                "type": "boolean",
                "default_value": False,
            }
        ]
        _update_yaml_file(integration_file, {"parameters": params})
        with mock.patch.object(
            constants,
            "EXCLUDED_NAMES_WHERE_SSL_DEFAULT_IS_NOT_TRUE",
            {"Mock Integration"},
        ):
            self.integration_runner.run(temp_integration)  # Should not raise

    @pytest.mark.parametrize("ssl_param_name", sorted(constants.VALID_SSL_PARAM_NAMES))
    def test_valid_ssl_parameter_names(
        self, temp_integration: pathlib.Path, ssl_param_name: str
    ) -> None:
        """Test that various valid SSL parameter names are accepted."""
        integration_file = temp_integration / constants.DEFINITION_FILE
        params = [
            {
                "name": ssl_param_name,
                "type": "boolean",
                "default_value": True,
            }
        ]
        _update_yaml_file(integration_file, {"parameters": params})

        self.integration_runner.run(temp_integration)  # Should not raise
