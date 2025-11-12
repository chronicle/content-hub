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
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

import mp.core.constants
from mp.core.data_models.action.parameter import (
    ActionParameter,
    ActionParamType,
    BuiltActionParameter,
    NonBuiltActionParameter,
)

st_valid_name = st.from_regex(r"^[a-zA-Z0-9-' ]+$").filter(
    lambda v: 0 < len(v) < mp.core.constants.PARAM_NAME_MAX_LENGTH
    and len(v.split()) <= mp.core.constants.PARAM_NAME_MAX_WORDS
)
st_excluded_name = st.sampled_from(
    sorted(mp.core.constants.EXCLUDED_PARAM_NAMES_WITH_TOO_MANY_WORDS)
)

st_valid_non_built_param_dict = st.fixed_dictionaries(
    # Required keys
    {
        "description": st.text(max_size=mp.core.constants.SHORT_DESCRIPTION_MAX_LENGTH),
        "is_mandatory": st.booleans(),
        "name": st.one_of(st_valid_name, st_excluded_name),
        "type": st.sampled_from(ActionParamType).map(lambda e: e.to_string()),
    },
    # Optional keys
    optional={
        "optional_values": st.lists(st.text()) | st.none(),
        "default_value": st.none() | st.text() | st.integers() | st.floats() | st.booleans(),
    },
)

st_valid_built_param_dict = st.fixed_dictionaries(
    # Required keys
    {
        "Description": st.text(max_size=mp.core.constants.SHORT_DESCRIPTION_MAX_LENGTH),
        "IsMandatory": st.booleans(),
        "Name": st.one_of(st_valid_name, st_excluded_name),
        "Type": st.sampled_from(ActionParamType).map(lambda e: str(e.value)),
    },
    # Optional keys
    optional={
        "OptionalValues": st.lists(st.text()) | st.none(),
        "DefaultValue": st.none() | st.text() | st.integers() | st.floats() | st.booleans(),
        "Value": st.none() | st.text() | st.integers() | st.floats() | st.booleans(),
    },
)


@st.composite
def _st_invalid_non_built_dict(draw: st.DrawFn) -> NonBuiltActionParameter:
    # Start with a valid dict
    data = draw(st_valid_non_built_param_dict)

    # Pick a random way to break it
    mutation = draw(
        st.sampled_from([
            "name_too_long",
            "name_bad_pattern",
            "name_too_many_words",
            "desc_too_long",
            "type_bad_string",
        ])
    )

    # Apply the mutation
    if mutation == "name_too_long":
        data["name"] = draw(
            st.text(min_size=mp.core.constants.PARAM_NAME_MAX_LENGTH + 1).filter(
                lambda s: s not in mp.core.constants.EXCLUDED_PARAM_NAMES_WITH_TOO_MANY_WORDS
            )
        )
    elif mutation == "name_bad_pattern":
        data["name"] = draw(st.just("!@#$%^"))
    elif mutation == "name_too_many_words":
        data["name"] = draw(
            st.text().filter(
                lambda s: (
                    len(s.split()) > mp.core.constants.PARAM_NAME_MAX_WORDS
                    and s not in mp.core.constants.EXCLUDED_PARAM_NAMES_WITH_TOO_MANY_WORDS
                )
            )
        )  # Fails AfterValidator
    elif mutation == "desc_too_long":
        data["description"] = draw(
            st.text(min_size=mp.core.constants.SHORT_DESCRIPTION_MAX_LENGTH + 1)
        )
    elif mutation == "type_bad_string":
        data["type"] = draw(st.just("NOT_A_REAL_TYPE"))

    return data


@st.composite
def _st_invalid_built_dict(draw: st.DrawFn) -> BuiltActionParameter:
    # Start with a valid dict
    data = draw(st_valid_built_param_dict)

    # Pick a random way to break it
    mutation = draw(
        st.sampled_from([
            "name_too_long",
            "name_bad_pattern",
            "name_too_many_words",
            "desc_too_long",
            "type_bad_int",
            "is_mandatory_bad_type",
        ])
    )

    # Apply the mutation
    if mutation == "name_too_long":
        data["Name"] = draw(st.text(min_size=mp.core.constants.PARAM_NAME_MAX_LENGTH + 1))
    elif mutation == "name_bad_pattern":
        data["Name"] = draw(st.just("!@#$%^"))
    elif mutation == "name_too_many_words":
        data["Name"] = draw(
            st.text().filter(
                lambda s: (
                    len(s.split()) > mp.core.constants.PARAM_NAME_MAX_WORDS
                    and s not in mp.core.constants.EXCLUDED_PARAM_NAMES_WITH_TOO_MANY_WORDS
                )
            )
        )
    elif mutation == "desc_too_long":
        data["Description"] = draw(
            st.text(min_size=mp.core.constants.SHORT_DESCRIPTION_MAX_LENGTH + 1)
        )
    elif mutation == "type_bad_int":
        data["Type"] = draw(
            st.integers().filter(lambda n: n not in {t.value for t in ActionParamType}).map(str)
        )
    elif mutation == "is_mandatory_bad_type":
        data["IsMandatory"] = draw(st.just("not a bool"))

    return data


class TestValidations:
    """
    Tests for pydantic-level model validations.
    """

    @given(valid_non_built=st_valid_non_built_param_dict)
    def test_valid_non_built(self, valid_non_built: NonBuiltActionParameter) -> None:
        ActionParameter.from_non_built(valid_non_built)

    @given(valid_built=st_valid_built_param_dict)
    def test_valid_built(self, valid_built: BuiltActionParameter) -> None:
        ActionParameter.from_built(valid_built)

    @given(valid_built=st_valid_built_param_dict)
    def test_recovery_from_built(self, valid_built: BuiltActionParameter) -> None:
        obj1 = ActionParameter.from_built(valid_built)

        # Convert to non-built and back to built
        non_built_dict = obj1.to_non_built()
        obj2 = ActionParameter.from_non_built(non_built_dict)

        assert obj1 == obj2

    @given(valid_non_built=st_valid_non_built_param_dict)
    def test_recovery_from_non_built(self, valid_non_built: NonBuiltActionParameter) -> None:
        obj1 = ActionParameter.from_non_built(valid_non_built)

        # Convert to built and back to non-built
        built_dict = obj1.to_built()
        obj2 = ActionParameter.from_built(built_dict)

        assert obj1 == obj2

    @given(invalid_non_built=_st_invalid_non_built_dict())
    def test_invalid_non_built_fails(self, invalid_non_built: NonBuiltActionParameter) -> None:
        with pytest.raises((ValidationError, KeyError, ValueError)):
            ActionParameter.from_non_built(invalid_non_built).to_non_built()

    @given(invalid_built=_st_invalid_built_dict())
    def test_invalid_built_fails(self, invalid_built: BuiltActionParameter) -> None:
        with pytest.raises((ValidationError, ValueError, KeyError)):
            ActionParameter.from_built(invalid_built).to_non_built()
