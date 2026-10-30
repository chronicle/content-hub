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
from unittest.mock import MagicMock, patch

from TIPCommon.data_models import CaseCloseComment

from crowd_strike_falcon.jobs.SyncAlerts import SyncAlerts


def test_case_close_comment_from_json_1p_multi_paragraph() -> None:
    """Test TIPCommon CaseCloseComment.from_json 1P caseWallRecords preserves
    multi-paragraph closure comments.
    """
    multi_paragraph_comment = (
        "First paragraph of analyst investigation notes.\n\n"
        "Second paragraph with additional indicators.\n"
        "Third line of details."
    )
    json_data = {
        "caseWallRecords": [
            {"activityDataJson": json.dumps({"comment": multi_paragraph_comment})}
        ]
    }

    result = CaseCloseComment.from_json(json_data)
    assert result.comment == multi_paragraph_comment


def test_case_close_comment_from_json_legacy_multi_paragraph() -> None:
    """Test TIPCommon CaseCloseComment.from_json Legacy objectsList response preserves
    multi-paragraph closure comments.
    """
    multi_paragraph_comment = "Paragraph 1\n\nParagraph 2\nParagraph 3"
    json_data = {
        "objectsList": [
            {
                "activityKind": 9,
                "description": (
                    "Case was closed by Admin.\n"
                    "Reason: Malicious\n"
                    "Root Cause: Other\n"
                    f"Comment: {multi_paragraph_comment}"
                ),
            }
        ]
    }

    result = CaseCloseComment.from_json(json_data)
    assert result.comment == multi_paragraph_comment


def test_get_secops_closure_comment_case_closed_and_alert_closed() -> None:
    """Test BaseSyncJob.get_secops_closure_comment returns full multi-paragraph text for
    both case closure and individual alert closure, and falls back when empty.
    """
    job = MagicMock(spec=SyncAlerts)
    job.soar_job = MagicMock()
    job.get_secops_closure_comment = SyncAlerts.get_secops_closure_comment.__get__(
        job
    )

    job_case = MagicMock()
    job_case.case_detail.id_ = "101"

    multi_line_text = "Investigation complete.\n\nConfirmed false positive."
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "caseWallRecords": [
            {"activityDataJson": json.dumps({"comment": multi_line_text})}
        ]
    }

    mock_client = MagicMock()
    mock_client.get_case_close_comment.return_value = mock_response

    with (
        patch(
            "TIPCommon.rest.soar_api.get_soar_client",
            return_value=mock_client,
        ),
        patch("TIPCommon.rest.soar_api.validate_response"),
    ):
        case_closed_comment = job.get_secops_closure_comment(
            job_case, {"is_case_closed": True}
        )
        assert case_closed_comment == multi_line_text

        alert_closed_comment = job.get_secops_closure_comment(
            job_case, {"is_case_closed": False, "comment": multi_line_text}
        )
        assert alert_closed_comment == multi_line_text

        fallback_comment = job.get_secops_closure_comment(
            job_case, {"is_case_closed": False, "comment": ""}
        )
        assert fallback_comment == "Case or Alert was closed"


def test_build_product_comments_for_closed_crowdstrike_alert() -> None:
    """Test _build_product_comments_for_alert syncs comments even when the
    CrowdStrike alert status is 'closed'.
    """
    job = MagicMock(spec=SyncAlerts)
    job._build_product_comments_for_alert = (
        SyncAlerts._build_product_comments_for_alert.__get__(job)
    )
    job._build_product_comments_from_detail = (
        SyncAlerts._build_product_comments_from_detail.__get__(job)
    )
    job._extract_comment_text = SyncAlerts._extract_comment_text.__get__(job)
    job._format_product_comment = SyncAlerts._format_product_comment.__get__(job)
    job._get_crowdstrike_ids_for_alert = MagicMock(return_value=["cs_alert_1"])

    product_detail = MagicMock()
    product_detail.composite_id = "cs_alert_1"
    product_detail.raw_data = {"status": "closed"}
    product_detail.comments = [
        "Crowdstrike cs_alert_1: Pre-closure investigation comment",
        "Crowdstrike cs_alert_1: Closing alert after remediation",
    ]
    job.fetched_product_details = {"101": [product_detail]}

    job_case = MagicMock()
    job_case.case_detail.id_ = "101"
    job_case._generate_string_hash.side_effect = lambda s: f"hash_{s}"
    job_case._is_valid_product_comment.return_value = True

    alert = MagicMock()
    alert.alert_group_identifier = "CrowdStrike_Alert_Group_1"

    result = job._build_product_comments_for_alert(
        job_case=job_case,
        alert=alert,
        product_comment_prefix="Crowdstrike ",
        case_comment_prefix="Google SecOps ",
        product_incident_key="composite_id",
        case_comments_hashes=set(),
    )

    assert len(result) == 2
    assert "Pre-closure investigation comment" in result[0]
    assert "Closing alert after remediation" in result[1]
