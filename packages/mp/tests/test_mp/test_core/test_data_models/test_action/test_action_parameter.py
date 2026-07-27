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

from mp.core.data_models.integrations.action.parameter import (
    ActionParameter,
    BuiltActionParameter,
    NonBuiltActionParameter,
)

from .strategies import (
    ST_VALID_BUILT_PARAM_DICT,
    ST_VALID_NON_BUILT_PARAM_DICT,
)


class TestValidations:
    """
    Tests for pydantic-level model validations.
    """

    @settings(max_examples=30)
    @given(valid_non_built=ST_VALID_NON_BUILT_PARAM_DICT)
    def test_valid_non_built(self, valid_non_built: NonBuiltActionParameter) -> None:
        ActionParameter.from_non_built(valid_non_built)

    @settings(max_examples=30)
    @given(valid_built=ST_VALID_BUILT_PARAM_DICT)
    def test_valid_built(self, valid_built: BuiltActionParameter) -> None:
        ActionParameter.from_built(valid_built)


class TestActionParameterValues:
    """
    Tests for ActionParameter value selection logic (Value vs DefaultValue).
    """

    def test_from_built_empty_value_picks_default(self) -> None:
        """Test that an empty string in 'Value' falls back to 'DefaultValue'."""
        built: BuiltActionParameter = {
            "Name": "test_param",
            "Description": "test desc",
            "IsMandatory": True,
            "Type": 0,  # STRING
            "Value": "",
            "DefaultValue": "functional_default",
            "OptionalValues": None,
        }
        param = ActionParameter.from_built(built)
        assert param.default_value == "functional_default"

    def test_from_built_none_value_picks_default(self) -> None:
        """Test that None in 'Value' falls back to 'DefaultValue'."""
        built: BuiltActionParameter = {
            "Name": "test_param",
            "Description": "test desc",
            "IsMandatory": True,
            "Type": 0,
            "Value": None,
            "DefaultValue": "functional_default",
            "OptionalValues": None,
        }
        param = ActionParameter.from_built(built)
        assert param.default_value == "functional_default"

    def test_from_built_present_value_overrides_default(self) -> None:
        """Test that a non-empty 'Value' is prioritized over 'DefaultValue'."""
        built: BuiltActionParameter = {
            "Name": "test_param",
            "Description": "test desc",
            "IsMandatory": True,
            "Type": 0,
            "Value": "user_value",
            "DefaultValue": "default_value",
            "OptionalValues": None,
        }
        param = ActionParameter.from_built(built)
        assert param.default_value == "user_value"

    def test_from_built_falsy_but_not_empty_value_preserved(self) -> None:
        """Test that numeric 0 or False in 'Value' is NOT treated as 'empty'."""
        # Test with 0
        built_zero: BuiltActionParameter = {
            "Name": "test_int",
            "Description": "test desc",
            "IsMandatory": True,
            "Type": 0,
            "Value": 0,
            "DefaultValue": 100,
            "OptionalValues": None,
        }
        param_zero = ActionParameter.from_built(built_zero)
        assert param_zero.default_value == 0

        # Test with False
        built_false: BuiltActionParameter = {
            "Name": "test_bool",
            "Description": "test desc",
            "IsMandatory": True,
            "Type": 1,  # BOOLEAN
            "Value": False,
            "DefaultValue": True,
            "OptionalValues": None,
        }
        param_false = ActionParameter.from_built(built_false)
        assert param_false.default_value is False
