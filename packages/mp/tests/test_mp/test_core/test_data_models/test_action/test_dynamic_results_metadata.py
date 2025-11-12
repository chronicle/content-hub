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

from mp.core.data_models.action.dynamic_results_metadata import (
    BuiltDynamicResultsMetadata,
    DynamicResultsMetadata,
    NonBuiltDynamicResultsMetadata,
)
from test_mp.test_core.test_data_models.utils import st_json_serializable, st_non_json_string

st_valid_built_dynamic_results_dict = st.fixed_dictionaries({
    "ResultExample": st.none() | st_json_serializable.map(json.dumps) | st.just(""),
    "ResultName": st.text(),
    "ShowResult": st.booleans(),
})

st_valid_non_built_dynamic_results_dict = st.fixed_dictionaries({
    "result_example_path": st.none() | st_json_serializable.map(json.dumps),
    "result_name": st.text(),
    "show_result": st.booleans(),
})


st_invalid_built_dynamic_results_dict = st.fixed_dictionaries({
    "ResultExample": st_non_json_string.filter(lambda s: s != ""),
    "ResultName": st.text(),
    "ShowResult": st.booleans(),
})

st_invalid_non_built_dynamic_results_dict = st.fixed_dictionaries({
    "result_example_path": st_non_json_string.filter(lambda s: s != ""),
    "result_name": st.text(),
    "show_result": st.booleans(),
})


class TestValidations:
    """
    Tests for pydantic-level model validations.
    """

    @settings(max_examples=30)
    @given(valid_non_built=st_valid_non_built_dynamic_results_dict)
    def test_valid_non_built(self, valid_non_built: NonBuiltDynamicResultsMetadata) -> None:
        DynamicResultsMetadata.from_non_built(valid_non_built).to_built()

    @settings(max_examples=30)
    @given(valid_built=st_valid_built_dynamic_results_dict)
    def test_valid_built(self, valid_built: BuiltDynamicResultsMetadata) -> None:
        DynamicResultsMetadata.from_built(valid_built).to_non_built()

    @settings(max_examples=30)
    @given(invalid_non_built=st_invalid_non_built_dynamic_results_dict)
    def test_invalid_non_built_fails(
        self, invalid_non_built: NonBuiltDynamicResultsMetadata
    ) -> None:
        with pytest.raises((ValidationError, KeyError, ValueError)):
            DynamicResultsMetadata.from_non_built(invalid_non_built)

    @settings(max_examples=30)
    @given(invalid_built=st_invalid_built_dynamic_results_dict)
    def test_invalid_built_fails(self, invalid_built: BuiltDynamicResultsMetadata) -> None:
        with pytest.raises((ValidationError, ValueError, KeyError)):
            DynamicResultsMetadata.from_built(invalid_built)
