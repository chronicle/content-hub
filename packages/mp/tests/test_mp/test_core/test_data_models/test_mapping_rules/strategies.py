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

from mp.core.data_models.integrations.mapping_rules.metadata import (
    ComparisonType,
    ExtractionFunction,
    TransformationFunction,
)
from test_mp.test_core.test_data_models.utils import (
    st_valid_built_type,
    st_valid_non_built_param_type,
)

# Strategies for MappingRule
ST_VALID_BUILT_MAPPING_RULE_DICT = st.fixed_dictionaries(
    {
        "Source": st.text() | st.none(),
        "Product": st.none() | st.text(),
        "EventName": st.none() | st.text(),
        "SecurityEventFieldName": st.text(),
        "TransformationFunction": st_valid_built_type(TransformationFunction),
        "TransformationFunctionParam": st.none() | st.text(),
        "RawDataPrimaryFieldComparisonType": st_valid_built_type(ComparisonType),
        "RawDataSecondaryFieldMatchTerm": st.none() | st.text(),
        "RawDataSecondaryFieldComparisonType": st_valid_built_type(ComparisonType),
        "RawDataThirdFieldMatchTerm": st.none() | st.text(),
        "RawDataThirdFieldComparisonType": st_valid_built_type(ComparisonType),
        "IsArtifact": st.booleans(),
    },
    optional={
        "RawDataPrimaryFieldMatchTerm": st.text() | st.none(),
        "ExtractionFunction": st_valid_built_type(ExtractionFunction),
        "ExtractionFunctionParam": st.none() | st.text(),
    },
)

ST_VALID_NON_BUILT_MAPPING_RULE_DICT = st.fixed_dictionaries(
    {
        "source": st.text(),
        "security_event_file_name": st.text(),
        "is_artifact": st.booleans(),
    },
    optional={
        "product": st.none() | st.text(),
        "event_name": st.none() | st.text(),
        "transformation_function": st_valid_non_built_param_type(TransformationFunction),
        "transformation_function_param": st.none() | st.text(),
        "raw_data_primary_field_match_term": st.text(),
        "raw_data_primary_field_comparison_type": st_valid_non_built_param_type(ComparisonType),
        "raw_data_secondary_field_match_term": st.none() | st.text(),
        "raw_data_secondary_field_comparison_type": st_valid_non_built_param_type(ComparisonType),
        "raw_data_third_field_match_term": st.none() | st.text(),
        "raw_data_third_field_comparison_type": st_valid_non_built_param_type(ComparisonType),
        "extract_function_param": st.none() | st.text(),
        "extract_function": st_valid_non_built_param_type(ExtractionFunction),
    },
)
