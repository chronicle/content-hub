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

"""Tests for the IntegrationHasDocumentationLinkValidation class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest

from mp.core import constants, file_utils
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.integrations import (
    IntegrationHasDocumentationLinkValidation,
)

if TYPE_CHECKING:
    import pathlib


def _update_yaml_file(file_path: pathlib.Path, updates: dict[str, Any]) -> None:
    """Read a YAML file, update its content, and write it back."""
    content = file_utils.load_yaml_file(file_path)
    content.update(updates)
    file_utils.write_yaml_to_file(content, file_path)


def _remove_key_from_yaml(file_path: pathlib.Path, key_to_remove: str) -> None:
    content = file_utils.load_yaml_file(file_path)
    if key_to_remove in content:
        del content[key_to_remove]
    file_utils.write_yaml_to_file(content, file_path)


class TestIntegrationHasDocumentationLinkValidation:
    """Test suite for the IntegrationHasDocumentationLinkValidation runner."""

    # Get an instance of the validator runner
    validator_runner = IntegrationHasDocumentationLinkValidation()

    def test_success_on_valid_integration(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration passes."""
        self.validator_runner.run(temp_integration)

    @pytest.mark.parametrize("invalid_value", ["", None])
    def test_failure_on_invalid_documentation_link(
        self, temp_integration: pathlib.Path, invalid_value: str | None
    ) -> None:
        """Test failure when the integration has an empty documentation link field."""
        integration_def_file = temp_integration / constants.DEFINITION_FILE
        _update_yaml_file(integration_def_file, {"documentation_link": invalid_value})

        with pytest.raises(NonFatalValidationError, match="missing a documentation link"):
            self.validator_runner.run(temp_integration)

    def test_failure_on_missing_documentation_link(self, temp_integration: pathlib.Path) -> None:
        """Test failure when the integration is missing a documentation link."""
        integration_def_file = temp_integration / constants.DEFINITION_FILE
        _remove_key_from_yaml(integration_def_file, "documentation_link")

        with pytest.raises(NonFatalValidationError, match="missing a documentation link"):
            self.validator_runner.run(temp_integration)

    def test_excluded_integrations_feature(self, temp_integration: pathlib.Path) -> None:
        """Test the excluded integrations feature works correctly."""
        integration_def_file = temp_integration / constants.DEFINITION_FILE
        _remove_key_from_yaml(integration_def_file, "documentation_link")

        with mock.patch.object(
            constants,
            "EXCLUDED_INTEGRATIONS_WITHOUT_DOCUMENTATION_LINK",
            {"mock_integration"},
        ):
            self.validator_runner.run(temp_integration)
