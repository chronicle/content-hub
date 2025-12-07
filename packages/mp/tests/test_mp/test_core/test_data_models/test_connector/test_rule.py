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

from hypothesis import given, settings

from mp.core.data_models.integrations.connector.rule import (
    BuiltConnectorRule,
    ConnectorRule,
    NonBuiltConnectorRule,
)

from .strategies import (
    ST_VALID_BUILT_CONNECTOR_RULE_DICT,
    ST_VALID_NON_BUILT_CONNECTOR_RULE_DICT,
)


class TestValidations:
    """
    Tests for pydantic-level model validations.
    """

    @settings(max_examples=30)
    @given(valid_non_built=ST_VALID_NON_BUILT_CONNECTOR_RULE_DICT)
    def test_valid_non_built(self, valid_non_built: NonBuiltConnectorRule) -> None:
        ConnectorRule.from_non_built(valid_non_built)

    @settings(max_examples=30)
    @given(valid_built=ST_VALID_BUILT_CONNECTOR_RULE_DICT)
    def test_valid_built(self, valid_built: BuiltConnectorRule) -> None:
        ConnectorRule.from_built(valid_built)
