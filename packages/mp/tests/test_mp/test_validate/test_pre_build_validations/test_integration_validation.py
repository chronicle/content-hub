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

from __future__ import annotations

import typing

import pytest

import mp.core.constants
import mp.core.file_utils
from mp.core.unix import NonFatalCommandError
from mp.validate.pre_build_validation.integration_validation import (
    IntegrationValidation,
)

if typing.TYPE_CHECKING:
    import pathlib

    from mp.core.custom_types import YamlFileContent


class TestIntegrationValidation:
    """Test suite for the IntegrationValidation runner."""

    def test_success_on_valid_integration(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration passes all checks."""
        IntegrationValidation.run(temp_integration)

    def test_failure_on_custom_integration(self, temp_integration: pathlib.Path) -> None:
        """Test that validation fails if the main definition marks the integration as custom."""
        # Mark the integration as custom
        definition_file = temp_integration / mp.core.constants.DEFINITION_FILE
        _update_yaml_file(definition_file, {"is_custom": True})

        with pytest.raises(NonFatalCommandError, match="contains custom components"):
            IntegrationValidation.run(temp_integration)

    def test_failure_on_custom_action(self, temp_integration: pathlib.Path) -> None:
        """Test that validation fails if a component is marked as custom."""
        # Mark the ping action as custom
        ping_def_file = (
            temp_integration
            / mp.core.constants.ACTIONS_DIR
            / f"ping{mp.core.constants.DEF_FILE_SUFFIX}"
        )
        _update_yaml_file(ping_def_file, {"is_custom": True})

        with pytest.raises(NonFatalCommandError, match="contains custom components"):
            IntegrationValidation.run(temp_integration)


def _update_yaml_file(file_path: pathlib.Path, updates: YamlFileContent) -> None:
    """Read a YAML file, update its content, and write it back using file_utils."""
    content: YamlFileContent = mp.core.file_utils.load_yaml_file(file_path)
    content.update(updates)
    mp.core.file_utils.write_yaml_to_file(content, file_path)
