# Copyright 2026 Google LLC
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

import pytest

from TIPCommon.data_models import CaseDetails, CasePriority
from TIPCommon.types import SingleJson


class TestCasePriority:
    """Unit tests for CasePriority enum and its string/protobuf parsing."""

    @pytest.mark.parametrize(
        ("value", "expected_member"),
        [
            (-1, CasePriority.INFORMATIVE),
            (0, CasePriority.UNCHANGED),
            (40, CasePriority.LOW),
            (60, CasePriority.MEDIUM),
            (80, CasePriority.HIGH),
            (100, CasePriority.CRITICAL),
        ],
    )
    def test_case_priority_integer_lookup(
        self,
        value: int,
        expected_member: CasePriority,
    ) -> None:
        """Test CasePriority enum lookup with valid integer values."""
        assert CasePriority(value) == expected_member

    @pytest.mark.parametrize(
        ("value", "expected_member"),
        [
            ("PriorityLow", CasePriority.LOW),
            ("PriorityMedium", CasePriority.MEDIUM),
            ("PriorityHigh", CasePriority.HIGH),
            ("PriorityCritical", CasePriority.CRITICAL),
            ("PriorityInfo", CasePriority.INFORMATIVE),
            ("PriorityUnspecified", CasePriority.UNCHANGED),
        ],
    )
    def test_case_priority_legacy_string_lookup(
        self,
        value: str,
        expected_member: CasePriority,
    ) -> None:
        """Test CasePriority lookup with legacy PascalCase strings."""
        assert CasePriority(value) == expected_member

    @pytest.mark.parametrize(
        ("value", "expected_member"),
        [
            ("PRIORITY_LOW", CasePriority.LOW),
            ("PRIORITY_MEDIUM", CasePriority.MEDIUM),
            ("PRIORITY_HIGH", CasePriority.HIGH),
            ("PRIORITY_CRITICAL", CasePriority.CRITICAL),
            ("PRIORITY_INFORMATIVE", CasePriority.INFORMATIVE),
            ("PRIORITY_INFO", CasePriority.INFORMATIVE),
            ("PRIORITY_UNSPECIFIED", CasePriority.UNCHANGED),
        ],
    )
    def test_case_priority_protobuf_string_lookup(
        self,
        value: str,
        expected_member: CasePriority,
    ) -> None:
        """Test CasePriority lookup with proto3 enum string formats."""
        assert CasePriority(value) == expected_member

    @pytest.mark.parametrize(
        ("value", "expected_member"),
        [
            ("LOW", CasePriority.LOW),
            ("MEDIUM", CasePriority.MEDIUM),
            ("HIGH", CasePriority.HIGH),
            ("CRITICAL", CasePriority.CRITICAL),
            ("INFORMATIVE", CasePriority.INFORMATIVE),
            ("UNCHANGED", CasePriority.UNCHANGED),
            ("low", CasePriority.LOW),
            ("medium", CasePriority.MEDIUM),
        ],
    )
    def test_case_priority_exact_names(
        self,
        value: str,
        expected_member: CasePriority,
    ) -> None:
        """Test CasePriority lookup with exact enum member names."""
        assert CasePriority(value) == expected_member

    @pytest.mark.parametrize(
        ("value", "expected_member"),
        [
            ("-1", CasePriority.INFORMATIVE),
            ("0", CasePriority.UNCHANGED),
            ("40", CasePriority.LOW),
            ("60", CasePriority.MEDIUM),
            ("80", CasePriority.HIGH),
            ("100", CasePriority.CRITICAL),
        ],
    )
    def test_case_priority_numeric_strings(
        self,
        value: str,
        expected_member: CasePriority,
    ) -> None:
        """Test CasePriority lookup with numeric string representations."""
        assert CasePriority(value) == expected_member

    @pytest.mark.parametrize("invalid_value", ["INVALID_PRIORITY", "999", 999])
    def test_case_priority_invalid_raises_value_error(
        self,
        invalid_value: str | int,
    ) -> None:
        """Test CasePriority raises ValueError for unsupported strings and integers."""
        with pytest.raises(ValueError, match="is not a valid CasePriority"):
            CasePriority(invalid_value)

    @pytest.mark.parametrize(
        ("priority_val", "expected_member"),
        [
            ("PRIORITY_MEDIUM", CasePriority.MEDIUM),
            ("PRIORITY_HIGH", CasePriority.HIGH),
            (60, CasePriority.MEDIUM),
            ("PriorityLow", CasePriority.LOW),
        ],
    )
    def test_case_details_from_json_with_priority(
        self,
        priority_val: str | int,
        expected_member: CasePriority,
    ) -> None:
        """Test CaseDetails.from_json parses priority across integer, legacy, and protobuf formats."""
        raw_json: SingleJson = {
            "id": 101,
            "displayName": "Test Case",
            "priority": priority_val,
        }
        case_details = CaseDetails.from_json(raw_json)
        assert case_details.priority == expected_member
