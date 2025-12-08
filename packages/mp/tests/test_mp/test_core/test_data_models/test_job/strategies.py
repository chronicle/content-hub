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

from hypothesis import strategies as st

import mp.core.constants
from mp.core.data_models.integrations.script.parameter import ScriptParamType
from test_mp.test_core.test_data_models.utils import (
    st_valid_built_param_type,
    st_valid_display_name,
    st_valid_identifier_name,
    st_valid_long_description,
    st_valid_non_built_param_type,
    st_valid_param_name,
    st_valid_short_description,
    st_valid_version,
)

# Strategies for JobParameter
ST_VALID_BUILT_JOB_PARAMETER_DICT = st.fixed_dictionaries(
    {
        "Name": st_valid_param_name,
        "IsMandatory": st.booleans(),
        "Type": st_valid_built_param_type(ScriptParamType),
    },
    optional={
        "DefaultValue": st.none() | st.text() | st.booleans() | st.floats() | st.integers(),
        "Description": st_valid_short_description,
    },
)

ST_VALID_NON_BUILT_JOB_PARAMETER_DICT = st.fixed_dictionaries(
    {
        "name": st_valid_param_name,
        "description": st_valid_short_description,
        "is_mandatory": st.booleans(),
        "type": st_valid_non_built_param_type(ScriptParamType),
    },
    optional={
        "default_value": st.none() | st.text() | st.booleans() | st.floats() | st.integers(),
    },
)

# Strategies for JobMetadata
ST_VALID_BUILT_JOB_METADATA_DICT = st.fixed_dictionaries(
    {
        "Creator": st.text(),
        "Description": st_valid_long_description,
        "Integration": st_valid_identifier_name,
        "Name": st_valid_display_name,
        "Parameters": st.lists(
            ST_VALID_BUILT_JOB_PARAMETER_DICT, max_size=mp.core.constants.MAX_PARAMETERS_LENGTH
        ),
        "RunIntervalInSeconds": st.integers(),
    },
    optional={
        "IsCustom": st.booleans(),
        "IsEnabled": st.booleans(),
        "Version": st_valid_version,
    },
)

ST_VALID_NON_BUILT_JOB_METADATA_DICT = st.fixed_dictionaries(
    {
        "creator": st.text(),
        "description": st_valid_long_description,
        "integration": st_valid_identifier_name,
        "name": st_valid_display_name,
        "parameters": st.lists(
            ST_VALID_NON_BUILT_JOB_PARAMETER_DICT, max_size=mp.core.constants.MAX_PARAMETERS_LENGTH
        ),
    },
    optional={
        "is_custom": st.booleans(),
        "is_enabled": st.booleans(),
        "run_interval_in_seconds": st.integers(),
        "version": st_valid_version,
    },
)
