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

"""Tests for the IntegrationHasMappingRulesIfHasConnectorValidation class."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import mp.core.constants
from mp.core import constants
from mp.core.exceptions import NonFatalValidationError
from mp.validate.pre_build_validation.integrations import (
    IntegrationHasMappingRulesIfHasConnectorValidation,
)

if TYPE_CHECKING:
    import pathlib


def _remove_file(file_path: pathlib.Path) -> None:
    file_path.unlink(missing_ok=True)


class TestMappingRulesValidation:
    """Test suite for the IntegrationHasMappingRulesIfHasConnectorValidation runner."""

    # Get an instance of the validator runner
    validator_runner = IntegrationHasMappingRulesIfHasConnectorValidation()

    def test_success_on_no_connector(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration (no connector) passes."""
        connector_def_file = (
            temp_integration
            / mp.core.constants.ACTIONS_DIR
            / f"connector{mp.core.constants.YAML_SUFFIX}"
        )
        _remove_file(connector_def_file)

        self.validator_runner.run(temp_integration)

    def test_success_on_connector_and_mapping_rules(self, temp_integration: pathlib.Path) -> None:
        """Test that a valid integration (connector and mapping rules exists) passes."""
        self.validator_runner.run(temp_integration)

    def test_failure_on_connector_no_mapping_rules(self, temp_integration: pathlib.Path) -> None:
        """Test failure when the integration has a connector but no mapping rules."""
        mapping_rules_def_file = temp_integration / constants.MAPPING_RULES_FILE
        _remove_file(mapping_rules_def_file)

        with pytest.raises(
            NonFatalValidationError, match="has connectors but doesn't have default mapping rules"
        ):
            self.validator_runner.run(temp_integration)
