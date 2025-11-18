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

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

import mp.core.constants
from mp.core.data_models.action.parameter import (
    ActionParameter,
    ActionParamType,
    BuiltActionParameter,
    NonBuiltActionParameter,
)
from test_mp.test_core.test_data_models.utils import (
    st_excluded_param_name,
    st_invalid_long_description,
    st_invalid_long_param_name,
    st_invalid_regex,
    st_invalid_too_many_words_param_name,
    st_valid_param_name,
    st_with_invalid_field,
)

st_valid_non_built_action_param_dict = st.fixed_dictionaries(
    # Required keys
    {
        "description": st.text(max_size=mp.core.constants.SHORT_DESCRIPTION_MAX_LENGTH),
        "is_mandatory": st.booleans(),
        "name": st.one_of(st_valid_param_name, st_excluded_param_name),
        "type": st.sampled_from(ActionParamType).map(lambda e: e.to_string()),
    },
    # Optional keys
    optional={
        "optional_values": st.lists(st.text()) | st.none(),
        "default_value": st.none() | st.text() | st.integers() | st.floats() | st.booleans(),
    },
)

st_valid_built_action_param_dict = st.fixed_dictionaries(
    # Required keys
    {
        "Description": st.text(max_size=mp.core.constants.SHORT_DESCRIPTION_MAX_LENGTH),
        "IsMandatory": st.booleans(),
        "Name": st.one_of(st_valid_param_name, st_excluded_param_name),
        "Type": st.sampled_from(ActionParamType).map(lambda e: str(e.value)),
    },
    # Optional keys
    optional={
        "OptionalValues": st.lists(st.text()) | st.none(),
        "DefaultValue": st.none() | st.text() | st.integers() | st.floats() | st.booleans(),
        "Value": st.none() | st.text() | st.integers() | st.floats() | st.booleans(),
    },
)

st_invalid_non_built_action_param_dict = st.one_of(
    st_with_invalid_field(
        st_valid_non_built_action_param_dict,
        "name",
        st_invalid_long_param_name(),
    ),
    st_with_invalid_field(st_valid_non_built_action_param_dict, "name", st_invalid_regex()),
    st_with_invalid_field(
        st_valid_non_built_action_param_dict,
        "name",
        st_invalid_too_many_words_param_name(),
    ),
    st_with_invalid_field(
        st_valid_non_built_action_param_dict,
        "description",
        st_invalid_long_description(),
    ),
    st_with_invalid_field(st_valid_non_built_action_param_dict, "type", st.just("NOT_A_REAL_TYPE")),
)

st_invalid_built_action_param_dict = st.one_of(
    st_with_invalid_field(
        st_valid_built_action_param_dict,
        "Name",
        st_invalid_long_param_name(),
    ),
    st_with_invalid_field(st_valid_built_action_param_dict, "Name", st_invalid_regex()),
    st_with_invalid_field(
        st_valid_built_action_param_dict,
        "Name",
        st_invalid_too_many_words_param_name(),
    ),
    st_with_invalid_field(
        st_valid_built_action_param_dict,
        "Description",
        st_invalid_long_description(),
    ),
    st_with_invalid_field(
        st_valid_built_action_param_dict,
        "Type",
        st.integers().filter(lambda n: n not in {t.value for t in ActionParamType}).map(str),
    ),
    st_with_invalid_field(st_valid_built_action_param_dict, "IsMandatory", st.just("not a bool")),
)


class TestValidations:
    """
    Tests for pydantic-level model validations.
    """

    @settings(max_examples=30)
    @given(valid_non_built=st_valid_non_built_action_param_dict)
    def test_valid_non_built(self, valid_non_built: NonBuiltActionParameter) -> None:
        ActionParameter.from_non_built(valid_non_built)

    @settings(max_examples=30)
    @given(valid_built=st_valid_built_action_param_dict)
    def test_valid_built(self, valid_built: BuiltActionParameter) -> None:
        ActionParameter.from_built(valid_built)

    @settings(max_examples=30)
    @given(valid_built=st_valid_built_action_param_dict)
    def test_recovery_from_built(self, valid_built: BuiltActionParameter) -> None:
        obj1 = ActionParameter.from_built(valid_built)

        # Convert to non-built and back to built
        non_built_dict = obj1.to_non_built()
        obj2 = ActionParameter.from_non_built(non_built_dict)

        assert obj1 == obj2

    @settings(max_examples=30)
    @given(valid_non_built=st_valid_non_built_action_param_dict)
    def test_recovery_from_non_built(self, valid_non_built: NonBuiltActionParameter) -> None:
        obj1 = ActionParameter.from_non_built(valid_non_built)

        # Convert to built and back to non-built
        built_dict = obj1.to_built()
        obj2 = ActionParameter.from_built(built_dict)

        assert obj1 == obj2

    @settings(max_examples=30)
    @given(invalid_non_built=st_invalid_non_built_action_param_dict)
    def test_invalid_non_built_fails(self, invalid_non_built: NonBuiltActionParameter) -> None:
        with pytest.raises((ValidationError, KeyError, ValueError)):
            ActionParameter.from_non_built(invalid_non_built)

    @settings(max_examples=30)
    @given(invalid_built=st_invalid_built_action_param_dict)
    def test_invalid_built_fails(self, invalid_built: BuiltActionParameter) -> None:
        with pytest.raises((ValidationError, ValueError, KeyError)):
            ActionParameter.from_built(invalid_built)
