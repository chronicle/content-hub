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
from mp.core.data_models.integrations.integration_meta.metadata import (
    MINIMUM_SYSTEM_VERSION,
    PythonVersion,
)
from mp.core.data_models.integrations.script.parameter import ScriptParamType
from test_mp.test_core.test_data_models.utils import (
    st_valid_built_param_type,
    st_valid_built_type,
    st_valid_display_name,
    st_valid_identifier_name,
    st_valid_long_description,
    st_valid_non_built_param_type,
    st_valid_param_name,
    st_valid_png_b64_string,
    st_valid_short_description,
    st_valid_svg_string,
    st_valid_url,
    st_valid_version,
)

ST_VALID_SYSTEM_VERSION = st.floats(min_value=MINIMUM_SYSTEM_VERSION)

# Strategies for IntegrationVisibilityProperty
ST_VALID_BUILT_INTEGRATION_VISIBILITY_PROPERTY_DICT = st.fixed_dictionaries({
    "Kind": st.sampled_from(["SystemMode", "FeatureFlag"]),
    "Value": st.sampled_from(["Nexus", "featEnableFederationSecondary"]),
})

ST_VALID_NON_BUILT_INTEGRATION_VISIBILITY_PROPERTY_DICT = st.fixed_dictionaries({
    "kind": st.sampled_from(["SystemMode", "FeatureFlag"]),
    "value": st.sampled_from(["Nexus", "featEnableFederationSecondary"]),
})

# Strategies for FeatureTags
ST_VALID_BUILT_FEATURE_TAGS_DICT = st.fixed_dictionaries({
    "IntegrationVisibilityProperties": st.lists(
        ST_VALID_BUILT_INTEGRATION_VISIBILITY_PROPERTY_DICT
    ),
})

ST_VALID_NON_BUILT_FEATURE_TAGS_DICT = st.fixed_dictionaries({
    "integration_visibility_properties": st.lists(
        ST_VALID_NON_BUILT_INTEGRATION_VISIBILITY_PROPERTY_DICT
    ),
})

# Strategies for IntegrationParameter
ST_VALID_BUILT_INTEGRATION_PARAMETER_DICT = st.fixed_dictionaries(
    {
        "PropertyName": st_valid_param_name,
        "Value": st.none() | st.text() | st.booleans() | st.floats() | st.integers(),
        "IsMandatory": st.booleans(),
        "PropertyType": st_valid_built_param_type(ScriptParamType),
        "IntegrationIdentifier": st_valid_identifier_name,
    },
    optional={
        "PropertyDescription": st_valid_short_description,
    },
)

ST_VALID_NON_BUILT_INTEGRATION_PARAMETER_DICT = st.fixed_dictionaries(
    {
        "name": st_valid_param_name,
        "description": st_valid_short_description,
        "is_mandatory": st.booleans(),
        "type": st_valid_non_built_param_type(ScriptParamType),
        "integration_identifier": st_valid_identifier_name,
    },
    optional={
        "default_value": st.none() | st.text() | st.booleans() | st.floats() | st.integers(),
    },
)

# Strategies for IntegrationMetadata
ST_VALID_BUILT_INTEGRATION_METADATA_DICT = st.fixed_dictionaries(
    {
        "Categories": st.lists(st.text()),
        "Description": st_valid_long_description,
        "DisplayName": st_valid_display_name,
        "PythonVersion": st_valid_built_type(PythonVersion),
        "DocumentationLink": st_valid_url,
        "Identifier": st_valid_identifier_name,
        "ImageBase64": st_valid_png_b64_string | st.none(),
        "IntegrationProperties": st.lists(
            ST_VALID_BUILT_INTEGRATION_PARAMETER_DICT,
            max_size=mp.core.constants.MAX_PARAMETERS_LENGTH,
        ),
        "ShouldInstalledInSystem": st.booleans(),
        "MarketingDisplayName": st_valid_display_name,
        "MinimumSystemVersion": ST_VALID_SYSTEM_VERSION,
        "SvgImage": st.none() | st_valid_svg_string,
        "Version": st_valid_version,
        "IsCertified": st.booleans(),
    },
    optional={
        "FeatureTags": st.none() | ST_VALID_BUILT_FEATURE_TAGS_DICT,
        "SVGImage": st_valid_svg_string,
        "IsAvailableForCommunity": st.booleans(),
        "IsCustom": st.booleans(),
        "IsPowerUp": st.booleans(),
    },
)

ST_VALID_NON_BUILT_INTEGRATION_METADATA_DICT = st.fixed_dictionaries(
    {
        "categories": st.lists(st.text()),
        "name": st_valid_display_name,
        "identifier": st_valid_identifier_name,
        "image_path": st_valid_png_b64_string,
        "parameters": st.lists(
            ST_VALID_NON_BUILT_INTEGRATION_PARAMETER_DICT,
            max_size=mp.core.constants.MAX_PARAMETERS_LENGTH,
        ),
    },
    optional={
        "description": st_valid_long_description,
        "feature_tags": st.none() | ST_VALID_NON_BUILT_FEATURE_TAGS_DICT,
        "python_version": st_valid_built_param_type(PythonVersion),
        "documentation_link": st_valid_url,
        "should_install_in_system": st.booleans(),
        "svg_logo_path": st.text(),
        "version": st_valid_version,
        "is_custom": st.booleans(),
        "is_available_for_community": st.booleans(),
        "is_powerup": st.booleans(),
    },
)
