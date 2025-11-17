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
from test_mp.test_core.test_data_models.utils import (
    FILE_NAME,
    st_invalid_long_description,
    st_invalid_long_identifier,
    st_invalid_regex,
    st_json_serializable,
    st_valid_identifier_name,
    st_with_invalid_field,
)

from .test_action_parameter import (
    st_invalid_built_action_param_dict,
    st_invalid_non_built_action_param_dict,
    st_valid_built_action_param_dict,
    st_valid_non_built_action_param_dict,
)
from .test_dynamic_results_metadata import (
    st_invalid_built_dynamic_results_dict,
    st_invalid_non_built_dynamic_results_dict,
    st_valid_built_dynamic_results_dict,
    st_valid_non_built_dynamic_results_dict,
)

st_valid_built_action_metadata_dict = st.fixed_dictionaries(
    {
        "Description": st.text(max_size=mp.core.constants.LONG_DESCRIPTION_MAX_LENGTH),
        "DynamicResultsMetadata": st.lists(st_valid_built_dynamic_results_dict),
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
        "dynamic_results_metadata": st.lists(st_valid_non_built_dynamic_results_dict),
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

st_invalid_non_built_dict = st.one_of(
    st_with_invalid_field(st_valid_non_built_action_metadata_dict, "name", st_invalid_regex()),
    st_with_invalid_field(
        st_valid_non_built_action_metadata_dict, "name", st_invalid_long_identifier()
    ),
    st_with_invalid_field(
        st_valid_non_built_action_metadata_dict, "integration_identifier", st_invalid_regex()
    ),
    st_with_invalid_field(
        st_valid_non_built_action_metadata_dict,
        "integration_identifier",
        st_invalid_long_identifier(),
    ),
    st_with_invalid_field(
        st_valid_non_built_action_metadata_dict, "description", st_invalid_long_description()
    ),
    st_with_invalid_field(
        st_valid_non_built_action_metadata_dict,
        "parameters",
        st.lists(
            st_valid_non_built_action_param_dict,
            min_size=mp.core.constants.MAX_PARAMETERS_LENGTH + 1,
        ),
    ),
    st_with_invalid_field(
        st_valid_non_built_action_metadata_dict,
        "parameters",
        st.lists(st_invalid_non_built_action_param_dict, min_size=1),
    ),
    st_with_invalid_field(
        st_valid_non_built_action_metadata_dict,
        "dynamic_results_metadata",
        st.lists(st_invalid_non_built_dynamic_results_dict, min_size=1),
    ),
)

st_invalid_built_dict = st.one_of(
    st_with_invalid_field(st_valid_built_action_metadata_dict, "Name", st_invalid_regex()),
    st_with_invalid_field(
        st_valid_built_action_metadata_dict,
        "Name",
        st_invalid_long_identifier(),
    ),
    st_with_invalid_field(
        st_valid_built_action_metadata_dict, "IntegrationIdentifier", st_invalid_regex()
    ),
    st_with_invalid_field(
        st_valid_built_action_metadata_dict,
        "IntegrationIdentifier",
        st_invalid_long_identifier(),
    ),
    st_with_invalid_field(
        st_valid_built_action_metadata_dict,
        "Description",
        st_invalid_long_description(),
    ),
    st_with_invalid_field(
        st_valid_built_action_metadata_dict,
        "Parameters",
        st.lists(
            st_valid_built_action_param_dict, min_size=mp.core.constants.MAX_PARAMETERS_LENGTH + 1
        ),
    ),
    st_with_invalid_field(
        st_valid_built_action_metadata_dict,
        "Parameters",
        st.lists(st_invalid_built_action_param_dict, min_size=1),
    ),
    st_with_invalid_field(
        st_valid_built_action_metadata_dict,
        "DynamicResultsMetadata",
        st.lists(st_invalid_built_dynamic_results_dict, min_size=1),
    ),
)


class TestValidations:
    """
    Tests for pydantic-level model validations.
    """

    @settings(max_examples=30)
    @given(valid_non_built=st_valid_non_built_action_metadata_dict)
    def test_valid_non_built(self, valid_non_built: NonBuiltActionMetadata) -> None:
        ActionMetadata.from_non_built(FILE_NAME, valid_non_built).to_built()

    @settings(max_examples=30)
    @given(valid_built=st_valid_built_action_metadata_dict)
    def test_valid_built(self, valid_built: BuiltActionMetadata) -> None:
        ActionMetadata.from_built(FILE_NAME, valid_built).to_non_built()

    @settings(max_examples=30)
    @given(invalid_built=st_invalid_built_dict)
    def test_invalid_built_fails(self, invalid_built: BuiltActionMetadata) -> None:
        with pytest.raises((ValidationError, ValueError, KeyError)):
            ActionMetadata.from_built(FILE_NAME, invalid_built)

    @settings(max_examples=30)
    @given(invalid_non_built=st_invalid_non_built_dict)
    def test_invalid_non_built_fails(self, invalid_non_built: NonBuiltActionMetadata) -> None:
        with pytest.raises((ValidationError, ValueError, KeyError)):
            ActionMetadata.from_non_built(FILE_NAME, invalid_non_built)
