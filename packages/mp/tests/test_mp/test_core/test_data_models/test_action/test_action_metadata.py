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

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

import mp.core.constants
from mp.core.data_models.action.metadata import (
    ActionMetadata,
    BuiltActionMetadata,
    NonBuiltActionMetadata,
)
from test_mp.test_core.test_data_models.utils import st_json_serializable, st_valid_identifier_name

from .test_action_parameter import (
    _st_invalid_built_action_param_dict,
    _st_invalid_non_built_action_param_dict,
    st_valid_built_action_param_dict,
    st_valid_non_built_action_param_dict,
)
from .test_dynamic_results_metadata import (
    st_invalid_built_dynamic_results_dict,
    st_invalid_non_built_dynamic_results_dict,
)
from .test_dynamic_results_metadata import (
    st_valid_built_dynamic_results_dict as st_valid_built_dynamic_results_metadata_dict,
)
from .test_dynamic_results_metadata import (
    st_valid_non_built_dynamic_results_dict as st_valid_non_built_dynamic_results_metadata_dict,
)

INVALID_MUTATIONS = [
    "name_bad_pattern",
    "name_too_long",
    "desc_too_long",
    "too_many_parameters",
    "invalid_parameter",
    "invalid_dynamic_result",
]

st_valid_built_action_metadata_dict = st.fixed_dictionaries(
    {
        "Description": st.text(max_size=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
        "DynamicResultsMetadata": st.lists(st_valid_built_dynamic_results_metadata_dict),
        "IntegrationIdentifier": st_valid_identifier_name,
        "Name": st_valid_identifier_name,
        "Parameters": st.lists(
            st_valid_built_action_param_dict, max_size=mp.core.constants.MAX_PARAMETERS_LENGTH
        ),
        "Creator": st.text(),
    },
    optional={
        "ScriptResultName": st.text() | st.none(),
        "SimulationDataJson": st.text() | st.none(),
        "DefaultResultValue": st.text() | st.none(),
        "Version": st.floats(allow_nan=False, allow_infinity=False),
        "IsAsync": st.booleans(),
        "IsCustom": st.booleans(),
        "IsEnabled": st.booleans(),
    },
)

st_valid_non_built_action_metadata_dict = st.fixed_dictionaries(
    {
        "description": st.text(max_size=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
        "dynamic_results_metadata": st.lists(st_valid_non_built_dynamic_results_metadata_dict),
        "integration_identifier": st_valid_identifier_name,
        "name": st_valid_identifier_name,
        "parameters": st.lists(
            st_valid_non_built_action_param_dict, max_size=mp.core.constants.MAX_PARAMETERS_LENGTH
        ),
    },
    optional={
        "is_async": st.booleans(),
        "is_custom": st.booleans(),
        "is_enabled": st.booleans(),
        "creator": st.text(),
        "script_result_name": st.text(),
        "simulation_data_json": st_json_serializable.map(json.dumps),
        "default_result_value": st.text() | st.none(),
        "version": st.floats(min_value=mp.core.constants.MINIMUM_SCRIPT_VERSION),
    },
)


@st.composite
def _st_invalid_non_built_dict(draw: st.DrawFn) -> NonBuiltActionMetadata:
    # Start with a valid dict
    data = draw(st_valid_non_built_action_metadata_dict)

    # Pick a random way to break it
    mutation = draw(st.sampled_from(INVALID_MUTATIONS))

    # Apply the mutation
    if mutation == "name_bad_pattern":
        data["name"] = draw(st.just("!@#$%^"))
    elif mutation == "name_too_long":
        data["name"] = draw(st.text(min_size=mp.core.constants.DISPLAY_NAME_MAX_LENGTH + 1))

    elif mutation == "desc_too_long":
        data["description"] = draw(
            st.text(min_size=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH + 1)
        )
    elif mutation == "too_many_parameters":
        data["parameters"] = draw(
            st.lists(
                st_valid_non_built_action_param_dict,
                min_size=mp.core.constants.MAX_PARAMETERS_LENGTH + 1,
            )
        )
    elif mutation == "invalid_parameter":
        data["parameters"] = draw(st.lists(_st_invalid_non_built_action_param_dict(), min_size=1))
    elif mutation == "invalid_dynamic_result":
        data["dynamic_results_metadata"] = draw(
            st.lists(st_invalid_non_built_dynamic_results_dict, min_size=1)
        )
    elif mutation == "integration_identifier_too_long":
        data["integration_identifier"] = draw(
            st.text(min_size=mp.core.constants.DISPLAY_NAME_MAX_LENGTH + 1)
        )

    elif mutation == "integration_identifier_bad_pattern":
        data["integration_identifier"] = draw(st.just("!@#$%^"))
    return data


@st.composite
def _st_invalid_built_dict(draw: st.DrawFn) -> BuiltActionMetadata:
    # Start with a valid dict
    data = draw(st_valid_built_action_metadata_dict)

    # Pick a random way to break it
    mutation = draw(st.sampled_from(INVALID_MUTATIONS))

    # Apply the mutation
    if mutation == "name_bad_pattern":
        data["Name"] = draw(st.just("!@#$%^"))
    elif mutation == "name_too_long":
        data["Name"] = draw(st.text(min_size=mp.core.constants.DISPLAY_NAME_MAX_LENGTH + 1))
    elif mutation == "desc_too_long":
        data["Description"] = draw(
            st.text(min_size=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH + 1)
        )
    elif mutation == "too_many_parameters":
        data["Parameters"] = draw(
            st.lists(
                st_valid_built_action_param_dict,
                min_size=mp.core.constants.MAX_PARAMETERS_LENGTH + 1,
            )
        )
    elif mutation == "invalid_parameter":
        data["Parameters"] = draw(st.lists(_st_invalid_built_action_param_dict(), min_size=1))
    elif mutation == "invalid_dynamic_result":
        data["DynamicResultsMetadata"] = draw(
            st.lists(st_invalid_built_dynamic_results_dict, min_size=1)
        )

    elif mutation == "integration_identifier_too_long":
        data["integration_identifier_bad_pattern"] = draw(
            st.text(min_size=mp.core.constants.DISPLAY_NAME_MAX_LENGTH + 1)
        )

    elif mutation == "integration_identifier_bad_pattern":
        data["integration_identifier_bad_pattern"] = draw(st.just("!@#$%^"))

    return data


class TestValidations:
    """
    Tests for pydantic-level model validations.
    """

    @settings(max_examples=30)
    @given(valid_non_built=st_valid_non_built_action_metadata_dict)
    def test_valid_non_built(self, valid_non_built: NonBuiltActionMetadata) -> None:
        ActionMetadata.from_non_built("test_name", valid_non_built).to_built()

    @settings(max_examples=30)
    @given(valid_built=st_valid_built_action_metadata_dict)
    def test_valid_built(self, valid_built: BuiltActionMetadata) -> None:
        ActionMetadata.from_built("test_name", valid_built).to_non_built()

    @settings(max_examples=30)
    @given(invalid_built=_st_invalid_built_dict())
    def test_invalid_built_fails(self, invalid_built: ActionMetadata) -> None:
        with pytest.raises((ValidationError, ValueError, KeyError)):
            ActionMetadata.from_built("test_name", invalid_built)

    @settings(max_examples=30)
    @given(invalid_non_built=_st_invalid_non_built_dict())
    def test_invalid_non_built_fails(self, invalid_non_built: ActionMetadata) -> None:
        with pytest.raises((ValidationError, ValueError, KeyError)):
            ActionMetadata.from_non_built("test_name", invalid_non_built)
