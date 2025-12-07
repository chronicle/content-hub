# Copyright 2025 Google LLC
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

from mp.core.data_models.integrations.connector.parameter import (
    ParamMode,
)
from mp.core.data_models.integrations.connector.rule import (
    ConnectorRuleType,
)
from mp.core.data_models.integrations.script.parameter import ScriptParamType
from test_mp.test_core.test_data_models.utils import (
    st_excluded_param_name,
    st_valid_built_param_type,
    st_valid_built_type,
    st_valid_display_name,
    st_valid_long_description,
    st_valid_non_built_param_type,
    st_valid_param_name,
    st_valid_short_description,
    st_valid_url,
    st_valid_version,
)

# Parameter Strategiesֿ
ST_VALID_NON_BUILT_CONNECTOR_PARAM_DICT = st.fixed_dictionaries(
    {
        "name": st.one_of(st_valid_param_name, st_excluded_param_name),
        "description": st_valid_short_description,
        "is_advanced": st.booleans(),
        "is_mandatory": st.booleans(),
        "type": st_valid_non_built_param_type(ScriptParamType),
        "mode": st_valid_non_built_param_type(ParamMode),
    },
    optional={
        "default_value": st.none() | st.text() | st.integers() | st.floats() | st.booleans(),
    },
)

ST_VALID_BUILT_CONNECTOR_PARAM_DICT = st.fixed_dictionaries(
    {
        "Name": st.one_of(st_valid_param_name, st_excluded_param_name),
        "Description": st_valid_short_description,
        "IsMandatory": st.booleans(),
        "Type": st_valid_built_param_type(ScriptParamType),
        "Mode": st_valid_built_type(ParamMode),
        "DefaultValue": st.none() | st.text() | st.integers() | st.floats() | st.booleans(),
    },
    optional={
        "IsAdvanced": st.booleans(),
    },
)


# Rule Strategies
ST_VALID_NON_BUILT_CONNECTOR_RULE_DICT = st.fixed_dictionaries({
    "rule_name": st_valid_display_name,
    "rule_type": st_valid_non_built_param_type(ConnectorRuleType),
})

ST_VALID_BUILT_CONNECTOR_RULE_DICT = st.fixed_dictionaries({
    "RuleName": st_valid_display_name,
    "RuleType": st_valid_built_type(ConnectorRuleType),
})


# Metadata Strategies
ST_VALID_NON_BUILT_CONNECTOR_METADATA_DICT = st.fixed_dictionaries(
    {
        "creator": st.text(),
        "description": st_valid_long_description,
        "integration": st.text(),
        "is_connector_rules_supported": st.booleans(),
        "name": st_valid_display_name,
        "parameters": st.lists(ST_VALID_NON_BUILT_CONNECTOR_PARAM_DICT),
        "rules": st.lists(ST_VALID_NON_BUILT_CONNECTOR_RULE_DICT),
    },
    optional={
        "is_custom": st.booleans(),
        "is_enabled": st.booleans(),
        "version": st_valid_version,
        "documentation_link": st_valid_url,
    },
)

ST_VALID_BUILT_CONNECTOR_METADATA_DICT = st.fixed_dictionaries(
    {
        "Creator": st.text(),
        "Description": st_valid_long_description,
        "DocumentationLink": st_valid_url,
        "Integration": st.text(),
        "IsConnectorRulesSupported": st.booleans(),
        "IsCustom": st.booleans(),
        "IsEnabled": st.booleans(),
        "Name": st_valid_display_name,
        "Parameters": st.lists(ST_VALID_BUILT_CONNECTOR_PARAM_DICT),
    },
    optional={
        "Rules": st.lists(ST_VALID_BUILT_CONNECTOR_RULE_DICT),
        "Version": st_valid_version,
    },
)
