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

import json
import types
from unittest.mock import MagicMock, patch

import pytest

from microsoft365_defender.core.Microsoft365DefenderExceptions import (
    Microsoft365DefenderException,
    NotFoundItemException,
)
from microsoft365_defender.core.UtilsManager import get_m365_alert_id_from_soar_alert

from microsoft365_defender.jobs.SyncAlerts import SyncAlerts
from microsoft365_defender.core.Microsoft365DefenderManager import (
    Microsoft365DefenderManager,
)


def test_get_alerts_by_ids_handles_404_gracefully():
    """Test that get_alerts_by_ids skips 404 alerts without raising an exception."""
    manager = MagicMock(spec=Microsoft365DefenderManager)
    manager.siemplify = MagicMock()
    manager.not_found_alert_ids = set()
    manager.get_alerts_by_ids = (
        Microsoft365DefenderManager.get_alerts_by_ids.__get__(manager)
    )

    def mock_get_alert(alert_id):
        if alert_id == "404_alert_id":
            raise NotFoundItemException(
                "Alert '404_alert_id' wasn't found in Microsoft 365 Defender."
            )
        alert = MagicMock()
        alert.alert_id = alert_id
        return alert

    manager.get_alert = mock_get_alert

    alert_ids = ["valid_alert_1", "404_alert_id", "valid_alert_2"]
    results = manager.get_alerts_by_ids(alert_ids)
    assert len(results) == 2
    assert [a.alert_id for a in results] == ["valid_alert_1", "valid_alert_2"]


def test_remove_synced_data_purges_404_alerts_from_state():
    """Test that remove_synced_data_from_db removes confirmed 404 alerts from state."""
    job = MagicMock(spec=SyncAlerts)
    job.soar_job = MagicMock()
    job.logger = MagicMock()
    job.manager = MagicMock()
    job.manager.not_found_alert_ids = {"invalid_alert_id"}
    job.processed_items = {"case_19": ["invalid_alert_id"]}
    job._remove_synced_entries = SyncAlerts._remove_synced_entries.__get__(job)
    job.remove_synced_data_from_db = (
        SyncAlerts.remove_synced_data_from_db.__get__(job)
    )

    job_case = MagicMock()
    job_case.case_detail.id_ = "case_19"
    mock_alert = MagicMock()
    mock_alert.alert_group_identifier = "invalid_alert_id"
    mock_alert.incident = MagicMock()
    mock_alert.incident.alert_id = "invalid_alert_id"
    job_case.case_detail.alerts = [mock_alert]

    product_details = []

    target_func = (
        "microsoft365_defender.jobs.SyncAlerts"
        ".get_m365_alert_id_from_soar_alert"
    )
    with patch(target_func, return_value="invalid_alert_id"):
        job.remove_synced_data_from_db(job_case, product_details)

    assert "case_19" not in job.processed_items


def test_remove_synced_data_retains_transient_fetch_failures():
    """Test that remove_synced_data_from_db retains alerts in state if missing
    due to transient fetch error.
    """
    job = MagicMock(spec=SyncAlerts)
    job.soar_job = MagicMock()
    job.logger = MagicMock()
    job.manager = MagicMock()
    job.manager.not_found_alert_ids = set()
    job.processed_items = {"case_19": ["glitched_alert_id"]}
    job._remove_synced_entries = SyncAlerts._remove_synced_entries.__get__(job)
    job.remove_synced_data_from_db = (
        SyncAlerts.remove_synced_data_from_db.__get__(job)
    )

    job_case = MagicMock()
    job_case.case_detail.id_ = "case_19"
    mock_alert = MagicMock()
    mock_alert.alert_group_identifier = "glitched_alert_id"
    mock_alert.incident = MagicMock()
    mock_alert.incident.alert_id = "glitched_alert_id"
    job_case.case_detail.alerts = [mock_alert]

    product_details = []

    target_func = (
        "microsoft365_defender.jobs.SyncAlerts"
        ".get_m365_alert_id_from_soar_alert"
    )
    with patch(target_func, return_value="glitched_alert_id"):
        job.remove_synced_data_from_db(job_case, product_details)

    assert "case_19" in job.processed_items
    assert "glitched_alert_id" in job.processed_items["case_19"]


def test_sync_case_status_to_product_handles_404():
    """Test that _sync_case_status_to_product catches NotFoundItemException."""
    job = MagicMock(spec=SyncAlerts)
    job.soar_job = MagicMock()
    job.logger = MagicMock()
    job.manager = MagicMock()
    job.manager.update_alert.side_effect = NotFoundItemException("Alert not found")
    job._remove_synced_entries = MagicMock()
    job._get_m365_closure_details = MagicMock(
        return_value=("truePositive", "maliciousUserActivity", False)
    )
    job.get_secops_closure_comment = MagicMock(return_value="Case closed")
    job._sync_case_status_to_product = (
        SyncAlerts._sync_case_status_to_product.__get__(job)
    )

    job_case = MagicMock()
    job_case.case_detail.id_ = "case_19"

    res = MagicMock()
    req = {
        "is_case_closed": False,
        "reason": "Malicious",
        "meta": MagicMock(incident_number="404_alert_id"),
    }
    res.incidents_to_close_in_product = [req]

    job._sync_case_status_to_product(res, job_case)
    job.logger.warn.assert_called_once()
    job._remove_synced_entries.assert_called_once_with(
        synced_list=[("case_19", "404_alert_id")]
    )


def test_push_comment_to_alert_handles_404():
    """Test that _push_comment_to_alert catches NotFoundItemException for 404 alert."""
    job = MagicMock(spec=SyncAlerts)
    job.logger = MagicMock()
    job.manager = MagicMock()
    job.manager.add_comment_to_alert.side_effect = NotFoundItemException(
        "Alert not found"
    )
    job._push_comment_to_alert = SyncAlerts._push_comment_to_alert.__get__(job)

    alert = MagicMock()
    alert.incident.alert_id = "404_alert_id"

    job._push_comment_to_alert(alert, "Test comment")
    job.logger.warn.assert_called_once()


def test_get_m365_alert_id_from_soar_alert_fallback_to_context_property():
    """Test get_m365_alert_id_from_soar_alert falls back to context property
    when DisplayId is missing or ticket_id is non-numeric.
    """
    soar_job = MagicMock()
    soar_job.get_context_property.return_value = "m365_context_alert_123"

    # Case 1: valid_ticket_id is True (numeric), but DisplayId is missing
    # in additional_properties
    alert_1 = MagicMock()
    alert_1.ticket_id = "12345"
    alert_1.additional_properties = json.dumps({})
    alert_1.alert_group_identifier = "group_1"

    alert_id_1 = get_m365_alert_id_from_soar_alert(soar_job, alert_1)
    assert alert_id_1 == "m365_context_alert_123"

    # Case 2: valid_ticket_id is False (non-numeric UUID), falls back
    # to context property
    alert_2 = MagicMock()
    alert_2.ticket_id = "c3a0d3d5-a90a-4095-a1f3-878568453594"
    alert_2.alert_group_identifier = "group_2"

    alert_id_2 = get_m365_alert_id_from_soar_alert(soar_job, alert_2)
    assert alert_id_2 == "m365_context_alert_123"


def test_parse_sync_directions_default():
    """Test parsing default sync directions."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.sync_direction = ""
        job._logger = MagicMock()

        directions = job._parse_sync_directions()
        assert directions == {
            "Status": "Bidirectional",
            "Comments": "Bidirectional",
        }


def test_parse_sync_directions_custom():
    """Test parsing custom sync directions."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.sync_direction = json.dumps(
            {"Status": "toXDR", "Comments": "toSecOps"}
        )
        job._logger = MagicMock()

        directions = job._parse_sync_directions()
        assert directions == {
            "Status": "toXDR",
            "Comments": "toSecOps",
        }


def test_parse_sync_directions_empty_value_returns_none():
    """Test that present key with empty string "" or "none" returns "None"."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.sync_direction = json.dumps(
            {"Status": "toXDR", "Comments": ""}
        )
        job._logger = MagicMock()

        directions = job._parse_sync_directions()
        assert directions == {
            "Status": "toXDR",
            "Comments": "None",
        }


def test_parse_sync_directions_omitted_key_defaults_to_bidirectional():
    """Test that omitted key entirely defaults to "Bidirectional"."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.sync_direction = json.dumps(
            {"Status": "toXDR"}
        )
        job._logger = MagicMock()

        directions = job._parse_sync_directions()
        assert directions == {
            "Status": "toXDR",
            "Comments": "Bidirectional",
        }


def test_parse_sync_directions_invalid_value_logs_and_returns_raw_string():
    """Test invalid direction value logs message and returns raw string."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.sync_direction = json.dumps(
            {"Status": "InvalidDirection", "Comments": "toSecOps"}
        )
        job._logger = MagicMock()

        directions = job._parse_sync_directions()
        assert directions == {
            "Status": "InvalidDirection",
            "Comments": "toSecOps",
        }
        job.logger.info.assert_called_with(
            "Invalid direction value 'InvalidDirection' provided. "
            "Supported values are: 'Bidirectional', 'toXDR', "
            "'toSecOps', 'None'."
        )


def test_parse_sync_directions_invalid_json_format():
    """Test invalid JSON for Sync Direction logs warning and skips sync."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.sync_direction = '{  "Status": "tes'
        job._logger = MagicMock()

        directions = job._parse_sync_directions()
        assert directions == {
            "Status": "Invalid",
            "Comments": "Invalid",
        }
        assert job.logger.info.called


def test_parse_closed_reason_mapping_default():
    """Test parsing default closed reason mapping."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.closed_reason_mapping = ""
        job._logger = MagicMock()

        mapping = job._parse_closed_reason_mapping()
        assert "Malicious" in mapping
        assert "Fallback" in mapping
        assert mapping["Fallback"] == {
            "classification": "unknownFutureValue",
            "determination": "other",
        }


def test_parse_closed_reason_mapping_missing_fallback_raises_exception():
    """Test that missing Fallback key or malformed JSON raises exception."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.closed_reason_mapping = '{  "Status": "tes}'
        job._logger = MagicMock()

        with pytest.raises(Microsoft365DefenderException):
            job._parse_closed_reason_mapping()
        assert job.logger.info.called


def test_get_m365_closure_details_matching_and_unclassified():
    """Test closure details matching with curly braces, case, and fallback."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.closed_reason_mapping = json.dumps(
            {
                "{Malicious | Misconfigured system}": {
                    "classification": "truePositive",
                    "determination": "malware",
                },
                "{NotMalicious | legit action}": {
                    "classification": "informationalExpectedActivity",
                    "determination": "securityTesting",
                },
                "Malicious": {
                    "classification": "truePositive",
                    "determination": "maliciousUserActivity",
                },
                "Fallback": {
                    "classification": "unknownFutureValue",
                    "determination": "other",
                },
            }
        )
        job._logger = MagicMock()

        # Priority 1: Match key with curly braces stripped
        c1, d1, fb1 = job._get_m365_closure_details(
            "Malicious", "Misconfigured system"
        )
        assert c1 == "truePositive"
        assert d1 == "malware"
        assert fb1 is False

        # Case-insensitive match
        c2, d2, fb2 = job._get_m365_closure_details(
            "NotMalicious", "Legit action"
        )
        assert c2 == "informationalExpectedActivity"
        assert d2 == "securityTesting"
        assert fb2 is False

        # Priority 3: Match single Reason key
        c3, d3, fb3 = job._get_m365_closure_details("Malicious", "Other")
        assert c3 == "truePositive"
        assert d3 == "maliciousUserActivity"
        assert fb3 is False

        # Priority 4: Unmapped match -> Fallback
        c4, d4, fb4 = job._get_m365_closure_details(
            "UnknownReason", "UnknownRootCause"
        )
        assert c4 == "unknownFutureValue"
        assert d4 == "other"
        assert fb4 is True


def test_to_camel_case_with_commas_and_spaces():
    """Test camelCase conversion for comma-separated or spaced strings."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        r1 = job._to_camel_case("Malicious, user activity")
        assert r1 == "maliciousUserActivity"
        assert job._to_camel_case("True, Positive") == "truePositive"
        r2 = job._to_camel_case("Not Malicious, False Positive")
        assert r2 == "notMaliciousFalsePositive"
        assert job._to_camel_case("newMaliciousAttack") == "newMaliciousAttack"
        assert job._to_camel_case("new malicious attack") == "newMaliciousAttack"


def test_get_m365_closure_details_empty_classification_uses_fallback():
    """Test empty classification logs and uses Fallback mapping."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.closed_reason_mapping = json.dumps(
            {
                "Malicious | Other": {
                    "classification": "",
                    "determination": None,
                },
                "Fallback": {
                    "classification": "TruePositive",
                    "determination": "maliciousUserActivity",
                },
            }
        )
        job._logger = MagicMock()

        c, d, fb = job._get_m365_closure_details("Malicious", "Other")
        assert c == "truePositive"
        assert d == "maliciousUserActivity"
        assert fb is True
        job.logger.info.assert_called_with(
            "No closure mapping entry found for 'Malicious | Other'. Using Fallback mapping."
        )


def test_get_m365_closure_details_unclassified_or_unknown_values_use_fallback():
    """Test classification or determination with unknown/unclassified values use Fallback."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.closed_reason_mapping = json.dumps(
            {
                "inconclusive| no clear conclusion": {
                    "classification": "Unclassified",
                    "determination": "other",
                },
                "notMalicious|unknown": {
                    "classification": None,
                    "determination": "",
                },
                "Malicious|unknown": {
                    "classification": "none",
                    "determination": None,
                },
                "Fallback": {
                    "classification": "unclassified",
                    "determination": "other",
                },
            }
        )
        job._logger = MagicMock()

        # Unclassified classification -> Uses Fallback
        c1, d1, fb1 = job._get_m365_closure_details("Inconclusive", "No clear conclusion")
        assert c1 == "unknownFutureValue"
        assert d1 == "other"
        assert fb1 is True

        # None / empty -> Uses Fallback
        c2, d2, fb2 = job._get_m365_closure_details("NotMalicious", "Unknown")
        assert c2 == "unknownFutureValue"
        assert d2 == "other"
        assert fb2 is True

        # "none" -> Uses Fallback
        c3, d3, fb3 = job._get_m365_closure_details("Malicious", "Unknown")
        assert c3 == "unknownFutureValue"
        assert d3 == "other"
        assert fb3 is True


def test_get_m365_closure_details_invalid_reason_or_root_cause_uses_fallback():
    """Test reason or root cause containing none, null, empty string goes to Fallback when unmapped."""
    with patch("TIPCommon.base.job.base_job.create_soar_job"):
        job = SyncAlerts()
        job._params = MagicMock()
        job._params.closed_reason_mapping = json.dumps(
            {
                "Malicious": {
                    "classification": "truePositive",
                    "determination": "malware",
                },
                "Fallback": {
                    "classification": "unclassified",
                    "determination": "other",
                },
            }
        )
        job._logger = MagicMock()

        # Invalid reason ("none") and no single reason mapping -> Fallback
        c1, d1, fb1 = job._get_m365_closure_details("none", "none")
        assert c1 == "unknownFutureValue"
        assert d1 == "other"
        assert fb1 is True
        job.logger.info.assert_called_with(
            "No closure mapping entry found for 'none | none'. Using Fallback mapping."
        )

        # Valid reason ("Malicious") with invalid root cause ("none") -> Fallback to single reason "Malicious"
        c2, d2, fb2 = job._get_m365_closure_details("Malicious", "none")
        assert c2 == "truePositive"
        assert d2 == "malware"
        assert fb2 is False

        # Invalid reason ("null") with no mapping -> Fallback
        c3, d3, fb3 = job._get_m365_closure_details("null", "")
        assert c3 == "unknownFutureValue"
        assert d3 == "other"
        assert fb3 is True


def test_sync_case_status_to_product_retries_with_fallback_on_api_error():
    """Test status sync retries with Fallback mapping on API error."""
    job = MagicMock(spec=SyncAlerts)
    job.soar_job = MagicMock()
    job.logger = MagicMock()
    job.manager = MagicMock()

    # Primary call fails, fallback call succeeds
    job.manager.update_alert.side_effect = [
        Exception("Invalid classification parameter"),
        None,
    ]
    job._remove_synced_entries = MagicMock()
    job._get_m365_closure_details = MagicMock(
        return_value=("TruePositive", "maliciousUserActivity", False)
    )
    job._get_m365_fallback_closure_details = MagicMock(
        return_value=("unknown", None)
    )
    job.get_secops_closure_comment = MagicMock(return_value="Case closed")
    job._sync_case_status_to_product = (
        SyncAlerts._sync_case_status_to_product.__get__(job)
    )

    job_case = MagicMock()
    job_case.case_detail.id_ = "case_100"

    res = MagicMock()
    req = {
        "is_case_closed": False,
        "reason": "Malicious",
        "root_cause": "Other",
        "meta": MagicMock(incident_number="alert_100"),
    }
    res.incidents_to_close_in_product = [req]

    job._sync_case_status_to_product(res, job_case)

    # Verify update_alert called twice: first with primary mapping, second with Fallback
    assert job.manager.update_alert.call_count == 2
    job.manager.update_alert.assert_any_call(
        "alert_100", "resolved", "TruePositive", "maliciousUserActivity"
    )
    job.manager.update_alert.assert_any_call(
        "alert_100", "resolved", "unknown", None
    )
    job.logger.warn.assert_called_once()


def test_get_secops_closure_comment_preserves_multiline_comments() -> None:
    """Test get_secops_closure_comment preserves multi-paragraph closure comments via TIPCommon."""
    job = MagicMock(spec=SyncAlerts)
    job.soar_job = MagicMock()
    job.get_secops_closure_comment = types.MethodType(
        SyncAlerts.get_secops_closure_comment, job
    )

    job_case = MagicMock()
    job_case.case_detail.id_ = "202"

    multi_line_text = "M365 Paragraph 1.\n\nM365 Paragraph 2.\nLine 3."
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
        result = job.get_secops_closure_comment(
            job_case, {"is_case_closed": True}
        )
        assert result == multi_line_text
