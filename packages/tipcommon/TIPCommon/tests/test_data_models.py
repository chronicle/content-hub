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

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from TIPCommon.data_models import CaseCloseComment, CaseDetails, CasePriority

if TYPE_CHECKING:
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


class TestCaseCloseComment:
    """Unit tests for CaseCloseComment parsing across Legacy and 1P responses."""

    def test_legacy_multiline_comment(self):
        json_data = {
            "objectsList": [
                {
                    "activityKind": 9,
                    "description": (
                        "Case closed root cause: Lab test\n"
                        "Reason: Not malicious\n"
                        "Comment: Line 1\nLine 2\n\nLine 3"
                    ),
                }
            ]
        }
        result = CaseCloseComment.from_json(json_data)
        assert result.comment == "Line 1\nLine 2\n\nLine 3"

    def test_1p_multiline_comment(self):
        json_data = {
            "caseWallRecords": [
                {
                    "activityDataJson": json.dumps(
                        {"comment": "Line 1\nLine 2\n\nLine 3"}
                    )
                }
            ]
        }
        result = CaseCloseComment.from_json(json_data)
        assert result.comment == "Line 1\nLine 2\n\nLine 3"

    @pytest.mark.parametrize(
        ("raw_description", "expected_comment"),
        [
            (
                "Case closed root cause: Lab test\n"
                "Reason: Not malicious\n"
                "Comment: Line 1\nLine 2 \n"
                "All attached playbooks and playbook blocks have been terminated.\n"
                "All Alerts were closed.",
                "Line 1\nLine 2",
            ),
            (
                "Case closed root cause: Lab test\n"
                "Reason: Not malicious\n"
                "Comment: Line 1\nLine 2\n"
                " Case closed by Siemplify API.\n"
                "All attached playbooks and playbook blocks have been terminated.\n"
                "All Alerts were closed.",
                "Line 1\nLine 2",
            ),
            (
                "Alert closed root cause: Other Reason: Malicious Usefulness: None "
                "Comment: Line 1\nLine 2\n"
                " All attached playbooks and playbook blocks have been terminated "
                "for this alert.",
                "Line 1\nLine 2",
            ),
        ],
    )
    def test_legacy_soar_footer_stripping(self, raw_description, expected_comment):
        json_data = {
            "objectsList": [
                {
                    "activityKind": 9,
                    "description": raw_description,
                }
            ]
        }
        result = CaseCloseComment.from_json(json_data)
        assert result.comment == expected_comment

    @pytest.mark.parametrize(
        ("raw_comment", "expected_comment"),
        [
            (
                "Line 1\nLine 2 \n"
                "All attached playbooks and playbook blocks have been terminated.\n"
                "All Alerts were closed.",
                "Line 1\nLine 2",
            ),
            (
                "Line 1\nLine 2\n"
                " Case closed by Siemplify API.\n"
                "All attached playbooks and playbook blocks have been terminated.\n"
                "All Alerts were closed.",
                "Line 1\nLine 2",
            ),
            (
                "Line 1\nLine 2\n"
                " All attached playbooks and playbook blocks have been terminated "
                "for this alert.",
                "Line 1\nLine 2",
            ),
        ],
    )
    def test_1p_soar_footer_stripping(self, raw_comment, expected_comment):
        json_data = {
            "caseWallRecords": [
                {"activityDataJson": json.dumps({"comment": raw_comment})}
            ]
        }
        result = CaseCloseComment.from_json(json_data)
        assert result.comment == expected_comment

    @pytest.mark.parametrize(
        "json_data",
        [
            {"objectsList": []},
            {"objectsList": [{"activityKind": 1, "description": "Comment: Ignored"}]},
            {"objectsList": [{"activityKind": 9, "description": ""}]},
            {"objectsList": [{"activityKind": 9, "description": None}]},
            {
                "objectsList": [
                    {
                        "activityKind": 9,
                        "description": (
                            "Case closed root cause: Lab test\n"
                            "Reason: Not malicious\n"
                            "Comment:   \n"
                            "All attached playbooks and playbook blocks have been terminated.\n"
                            "All Alerts were closed."
                        ),
                    }
                ]
            },
        ],
    )
    def test_legacy_empty_comments(self, json_data):
        result = CaseCloseComment.from_json(json_data)
        assert result.comment == ""

    @pytest.mark.parametrize(
        "json_data",
        [
            {},
            {"caseWallRecords": []},
            {"caseWallRecords": [{"activityDataJson": "{}"}]},
            {"caseWallRecords": [{"activityDataJson": "invalid-json"}]},
            {"caseWallRecords": [{"activityDataJson": None}]},
            {"caseWallRecords": [{"activityDataJson": json.dumps({"comment": ""})}]},
            {"caseWallRecords": [{"activityDataJson": json.dumps({"comment": None})}]},
            {
                "caseWallRecords": [
                    {
                        "activityDataJson": json.dumps(
                            {
                                "comment": (
                                    "  \nAll attached playbooks and playbook blocks "
                                    "have been terminated.\nAll Alerts were closed."
                                )
                            }
                        )
                    }
                ]
            },
        ],
    )
    def test_1p_empty_comments(self, json_data):
        result = CaseCloseComment.from_json(json_data)
        assert result.comment == ""
