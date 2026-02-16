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

from mp.core.data_models.integrations.integration_meta.parameter import (
    BuiltIntegrationParameter,
    IntegrationParameter,
    NonBuiltIntegrationParameter,
)

from .strategies import (
    ST_VALID_BUILT_INTEGRATION_PARAMETER_DICT,
    ST_VALID_NON_BUILT_INTEGRATION_PARAMETER_DICT,
)


class TestValidations:
    """
    Tests for pydantic-level model validations.
    """

    @settings(max_examples=30)
    @given(valid_non_built=ST_VALID_NON_BUILT_INTEGRATION_PARAMETER_DICT)
    def test_valid_non_built(self, valid_non_built: NonBuiltIntegrationParameter) -> None:
        IntegrationParameter.from_non_built(valid_non_built)

    @settings(max_examples=30)
    @given(valid_built=ST_VALID_BUILT_INTEGRATION_PARAMETER_DICT)
    def test_valid_built(self, valid_built: BuiltIntegrationParameter) -> None:
        IntegrationParameter.from_built(valid_built)


class TestConversions:
    """
    Tests for conversions between built, non-built, and the pydantic model.
    """

    def test_round_trip_preserves_display_name(self) -> None:
        """
        Tests that converting from built -> non-built -> built preserves the
        original `PropertyDisplayName`.
        """
        original_built: BuiltIntegrationParameter = {
            "PropertyName": "param_name",
            "PropertyDisplayName": "My Display Name",
            "Value": "default value",
            "PropertyDescription": "This is a test parameter.",
            "IsMandatory": True,
            "PropertyType": 2,
            "IntegrationIdentifier": "test_integration",
        }

        # built -> model -> non-built -> model -> built
        final_built = IntegrationParameter.from_non_built(
            IntegrationParameter.from_built(original_built).to_non_built()
        ).to_built()

        assert final_built["PropertyDisplayName"] == original_built["PropertyDisplayName"]
