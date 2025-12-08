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

from hypothesis import strategies as st

import mp.core.constants
from mp.core.data_models.integrations.action.parameter import (
    ActionParamType,
)
from test_mp.test_core.test_data_models.utils import (
    st_excluded_param_name,
    st_json_serializable,
    st_valid_display_name,
    st_valid_identifier_name,
    st_valid_param_name,
    st_valid_short_description,
    st_valid_version,
)

# Strategies for dynamic_results_metadata
ST_VALID_BUILT_DYNAMIC_RESULTS_DICT = st.fixed_dictionaries({
    "ResultExample": st.none() | st_json_serializable.map(json.dumps) | st.just(""),
    "ResultName": st.text(),
    "ShowResult": st.booleans(),
})

ST_VALID_NON_BUILT_DYNAMIC_RESULTS_DICT = st.fixed_dictionaries({
    "result_example_path": st.none() | st_json_serializable.map(json.dumps),
    "result_name": st.text(),
    "show_result": st.booleans(),
})

# Strategies for action_parameter

ST_VALID_NON_BUILT_PARAM_DICT = st.fixed_dictionaries(
    # Required keys
    {
        "description": st_valid_short_description,
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

ST_VALID_BUILT_PARAM_DICT = st.fixed_dictionaries(
    # Required keys
    {
        "Description": st_valid_short_description,
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


# Strategies for action_metadata
ST_VALID_BUILT_ACTION_METADATA_DICT = st.fixed_dictionaries(
    {
        "Description": st_valid_short_description,
        "DynamicResultsMetadata": st.lists(ST_VALID_BUILT_DYNAMIC_RESULTS_DICT),
        "IntegrationIdentifier": st_valid_identifier_name,
        "Name": st_valid_display_name,
        "Parameters": st.lists(
            ST_VALID_BUILT_PARAM_DICT, max_size=mp.core.constants.MAX_PARAMETERS_LENGTH
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

ST_VALID_NON_BUILT_ACTION_METADATA_DICT = st.fixed_dictionaries(
    {
        "description": st_valid_short_description,
        "dynamic_results_metadata": st.lists(ST_VALID_NON_BUILT_DYNAMIC_RESULTS_DICT),
        "integration_identifier": st_valid_identifier_name,
        "name": st_valid_display_name,
        "parameters": st.lists(
            ST_VALID_NON_BUILT_PARAM_DICT, max_size=mp.core.constants.MAX_PARAMETERS_LENGTH
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
        "version": st_valid_version,
    },
)
