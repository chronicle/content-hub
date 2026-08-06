# ruff: file-ignore[too-many-arguments, too-many-positional-arguments]
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
from unittest.mock import MagicMock, PropertyMock, patch

from TIPCommon.base.job.job_case import JobCase, SyncMetadata
from TIPCommon.data_models import AlertCard, CaseDataStatus, CaseDetails, UserProfileCard

from wiz.core.constants import SYNC_JOB_IDENTIFIER, SYNC_JOB_SCRIPT_NAME
from wiz.core.datamodels import Issue, WizIncidentComment
from wiz.jobs.wiz_secops_bidirectional_sync_job import (
    WizSecopsBidirectionalSyncJob,
)


def _make_job() -> WizSecopsBidirectionalSyncJob:
    """Create a Wiz sync job instance with mocked SOAR internals."""
    job = WizSecopsBidirectionalSyncJob.__new__(WizSecopsBidirectionalSyncJob)
    job._name = SYNC_JOB_SCRIPT_NAME
    job.context_identifier = SYNC_JOB_IDENTIFIER
    job.tags_identifiers = ["Wiz"]
    job.sync_status_enabled = True
    job.sync_comments_enabled = True
    job.sync_product_link_enabled = True
    job.sync_severity_enabled = True
    job.failed_cases = set()
    job._escalated_threats = set()

    # Mock logger
    type(job).logger = PropertyMock(return_value=MagicMock())

    # Mock self.params
    mock_params = MagicMock()
    mock_params.environment_name = "Default Environment"
    mock_params.fields_to_sync = "Status, Comments, Product Link, Severity"
    type(job).params = PropertyMock(return_value=mock_params)

    # Mock self.soar_job
    job._soar_job = MagicMock()

    # Mock self.api_client
    job._api_client = MagicMock()

    return job


def _make_mock_alert(
    identifier: str,
    alert_group_identifier: str | None,
    status: str = "open",
    priority: str = "Medium",
    name: str = "Wiz Alert",
) -> AlertCard:
    alert = MagicMock(spec=AlertCard)
    alert.identifier = identifier
    alert.alert_group_identifier = alert_group_identifier
    alert.additional_properties = (
        json.dumps(
            {
                "security_result_threat_id": alert_group_identifier,
                "SourceGroupingIdentifier": alert_group_identifier,
            }
        )
        if alert_group_identifier
        else None
    )
    alert.status = status
    alert.priority = priority
    alert.name = name
    alert.incident = None
    return alert


def _make_mock_case(
    case_id: int,
    alerts: list[AlertCard],
    status: str = CaseDataStatus.OPENED,
    comments: list[dict] | None = None,
    close_reason: str = "REASON_UNSPECIFIED",
    close_verdict: int = 0,
) -> CaseDetails:
    case = MagicMock(spec=CaseDetails)
    case.id_ = case_id
    case.alerts = alerts
    case.status = status
    case.comments = comments or []
    case.close_reason = close_reason
    case.close_verdict = close_verdict
    case.tags = [{"displayName": "Wiz"}]
    return case


# -------------------------------------------------------------------
# Test Cases
# -------------------------------------------------------------------


class TestWizSecopsBidirectionalSyncJob:
    def test_init_api_clients_parses_fields_to_sync(self) -> None:
        """Verifies that init_api_clients parses fields to sync parameter correctly."""
        job = _make_job()
        job.params.fields_to_sync = "Status, Comments"

        with patch("secret_manager.core.action_init" if False else "wiz.core.action_init.create_api_client"):
            job._init_api_clients()
            assert job.sync_status_enabled is True
            assert job.sync_comments_enabled is True
            assert job.sync_product_link_enabled is False
            assert job.sync_severity_enabled is False

    def test_sync_status_inbound_wiz_only_closes_case(self) -> None:
        """Verifies that RESOLVED Wiz Threat closes all Wiz alerts and the overall case if no other alerts exist."""
        job = _make_job()
        alerts = [
            _make_mock_alert("alert_1", "wiz_threat_1", status="open"),
        ]
        case = _make_mock_case(1234, alerts)
        job_case = JobCase(case_detail=case, modification_time=1000)
        job_case.product_ids_from_secops_alerts = {"wiz_threat_1": alerts[0]}
        job_case.alert_metadata["alert_1"] = SyncMetadata(status="RESOLVED")

        def mock_close_status(
            root_cause: str, comment: str, reason: str, case_id: str, alert_id: str
        ) -> None:
            alerts[0].status = "closed"

        job.soar_job.close_alert = mock_close_status

        job.sync_status(job_case)

        job.soar_job.close_case.assert_called_once_with(
            root_cause="Other",
            case_id=1234,
            reason="Closed by Wiz Sync",
            comment="[SecOps & Wiz Sync Job] All alerts closed. Closing the case.",
            alert_identifier=None,
        )

    def test_sync_status_inbound_mixed_alerts_leaves_case_open(self) -> None:
        """Verifies that RESOLVED Wiz Threat closes Wiz alerts but leaves the case open.

        Leaves open if active non-Wiz alerts exist.
        """
        job = _make_job()
        alerts = [
            _make_mock_alert("alert_1", "wiz_threat_1", status="open"),
            _make_mock_alert("alert_2", None, status="open"),
        ]
        case = _make_mock_case(1234, alerts)
        job_case = JobCase(case_detail=case, modification_time=1000)
        job_case.product_ids_from_secops_alerts = {"wiz_threat_1": alerts[0]}
        job_case.alert_metadata["alert_1"] = SyncMetadata(status="RESOLVED")

        def mock_close_status(
            root_cause: str, comment: str, reason: str, case_id: str, alert_id: str
        ) -> None:
            alerts[0].status = "closed"

        job.soar_job.close_alert = mock_close_status

        job.sync_status(job_case)

        job.soar_job.close_case.assert_not_called()

        job.soar_job.add_comment.assert_called_once()
        _args, kwargs = job.soar_job.add_comment.call_args
        assert kwargs["case_id"] == 1234
        assert "Mixed Alert Resolution" in kwargs["comment"]

    def test_sync_status_outbound(self) -> None:
        """Verifies outbound status changes and audit comments posted to both systems."""
        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1")]
        case = _make_mock_case(1234, alerts, status=CaseDataStatus.CLOSED, close_reason="REASON_MALICIOUS")
        job_case = JobCase(case_detail=case, modification_time=1000)
        job_case.product_ids_from_secops_alerts = {"wiz_threat_1": alerts[0]}
        job_case.alert_metadata["alert_1"] = SyncMetadata(status="OPEN")

        job.sync_status(job_case)

        job.api_client.resolve_issue.assert_called_once_with(
            issue_id="wiz_threat_1",
            resolution_reason="Malicious Threat",
            resolution_note="Closed via SecOps Case Sync",
        )
        job.soar_job.add_comment.assert_called_once()
        assert "status was updated to CLOSED" in job.soar_job.add_comment.call_args[1]["comment"]
        job.api_client.add_comment_to_issue.assert_called_once()
        assert "status was updated to CLOSED" in job.api_client.add_comment_to_issue.call_args[1]["comment"]

    def test_sync_severity(self) -> None:
        """Verifies severity synchronization including escalation and ignored downgrades with comments."""
        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1", priority="Medium")]
        case = _make_mock_case(1234, alerts)
        job_case = JobCase(case_detail=case, modification_time=1000)
        job_case.alert_metadata["alert_1"] = SyncMetadata(severity="CRITICAL")

        job.sync_severity_to_case = MagicMock()
        job.sync_severity(job_case)

        job.sync_severity_to_case.assert_called_once_with(
            alert_identifier="alert_1",
            alert_name="Wiz Alert",
            case_id="1234",
            new_priority="Critical",
        )
        job.soar_job.add_comment.assert_called_once()
        assert "Severity Escalation" in job.soar_job.add_comment.call_args[1]["comment"]

        job2 = _make_job()
        alerts2 = [_make_mock_alert("alert_1", "wiz_threat_1", priority="High")]
        case2 = _make_mock_case(1234, alerts2)
        job_case2 = JobCase(case_detail=case2, modification_time=1000)
        job_case2.alert_metadata["alert_1"] = SyncMetadata(severity="MEDIUM")

        job2.sync_severity_to_case = MagicMock()
        job2.sync_severity(job_case2)

        job2.sync_severity_to_case.assert_not_called()
        job2.soar_job.add_comment.assert_called_once()
        assert "Severity Downgrade Ignored" in job2.soar_job.add_comment.call_args[1]["comment"]

    def test_sync_comments_loop_back_prevention(self) -> None:
        """Verifies that sync comments ignores loopback comments originating from sync job."""
        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1")]
        comments = [
            {"comment": "[SecOps & Wiz Sync Job] wiz_threat_1: note from Wiz", "creator": "sync@soar.com"},
            {"comment": "analyst comment on Case", "creator": "analyst@company.com"},
        ]
        case = _make_mock_case(1234, alerts, comments=comments)
        job_case = JobCase(case_detail=case, modification_time=1000)

        issue_comments = [
            WizIncidentComment({"id": "1", "text": "[SecOps & Wiz Sync Job] user wrote: comment text"}),
            WizIncidentComment({"id": "2", "text": "analyst comment in Wiz"}),
        ]
        issue = Issue(
            raw_data={},
            issue_id="wiz_threat_1",
            comments=issue_comments,
        )
        job_case.product_ids_from_secops_alerts = {"wiz_threat_1": alerts[0]}
        job_case.add_product_incident(issue, product_key="issue_id")

        job.sync_product_comments_to_case = MagicMock()
        job.sync_case_comments_to_product = MagicMock()
        job.soar_job.fetch_case_comments = MagicMock(return_value=comments)

        job.sync_comments(job_case)

        job.sync_case_comments_to_product.assert_called_once()
        synced_comments = job.sync_case_comments_to_product.call_args[1]["comments"]
        assert len(synced_comments) == 1
        assert "analyst comment on Case" in synced_comments[0]

        job.sync_product_comments_to_case.assert_called_once()
        synced_wiz_comments = job.sync_product_comments_to_case.call_args[1]["comments"]
        assert len(synced_wiz_comments) == 1
        assert "analyst comment in Wiz" in synced_wiz_comments[0]

    def test_sync_comments_ignores_system_audit_comments(self) -> None:
        """Verifies that system audit comments (starting with job prefix) are ignored in outbound sync."""
        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1")]
        comments = [
            {"comment": "analyst comment on Case", "creator": "analyst@company.com"},
            {"comment": "[SecOps & Wiz Sync Job] Severity Escalation. Mapped Wiz Threat...", "creator": "system"},
        ]
        case = _make_mock_case(1234, alerts, comments=comments)
        job_case = JobCase(case_detail=case, modification_time=1000)

        job.api_client.add_comment_to_issue = MagicMock()
        job.sync_product_comments_to_case = MagicMock()

        job_case.case_comments = comments
        job.soar_job.fetch_case_comments = MagicMock(return_value=comments)

        job.sync_comments(job_case)

        job.api_client.add_comment_to_issue.assert_called_once()
        _, kwargs = job.api_client.add_comment_to_issue.call_args
        assert "analyst comment on Case" in kwargs["comment"]
        assert "Severity Escalation" not in kwargs["comment"]

    def test_sync_comments_exact_match_prevention(self) -> None:
        """Verifies that comments with substring prefixes are matched exactly and not treated as duplicates."""
        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1")]
        comments = [
            {
                "comment": "Hi, I'm from SecOps!",
                "creator": "analyst@company.com",
                "creation_time_unix_time_in_ms": 1000,
            },
            {
                "comment": "Hi, I'm from SecOps! 2",
                "creator": "analyst@company.com",
                "creation_time_unix_time_in_ms": 2000,
            },
        ]
        case = _make_mock_case(1234, alerts, comments=comments)
        job_case = JobCase(case_detail=case, modification_time=1000)

        comment_text = (
            "[SecOps & Wiz Sync Job] analyst@company.com wrote in Google SecOps on "
            "1970-01-01T00:00:01+00:00: Hi, I'm from SecOps!"
        )
        issue_comments = [
            WizIncidentComment({"id": "1", "text": comment_text}),
        ]
        issue = Issue(
            raw_data={},
            issue_id="wiz_threat_1",
            comments=issue_comments,
        )
        job_case.product_ids_from_secops_alerts = {"wiz_threat_1": alerts[0]}
        job_case.add_product_incident(issue, product_key="issue_id")

        job.api_client.add_comment_to_issue = MagicMock()
        job.sync_product_comments_to_case = MagicMock()
        job.soar_job.fetch_case_comments = MagicMock(return_value=comments)

        job.sync_comments(job_case)

        job.api_client.add_comment_to_issue.assert_called_once()
        _, kwargs = job.api_client.add_comment_to_issue.call_args
        assert "Hi, I'm from SecOps! 2" in kwargs["comment"]

    def test_sync_status_inbound_multiple_alerts_same_threat(self) -> None:
        """Verifies that closing a Wiz Threat closes all Wiz alerts matching that threat."""
        job = _make_job()
        alerts = [
            _make_mock_alert("alert_1", "wiz_threat_1", status="open"),
            _make_mock_alert("alert_2", "wiz_threat_1", status="open"),
        ]
        case = _make_mock_case(1234, alerts)
        job_case = JobCase(case_detail=case, modification_time=1000)
        job._map_alerts_to_threat_ids(job_case)
        job_case.alert_metadata["alert_1"] = SyncMetadata(status="RESOLVED")
        job_case.alert_metadata["alert_2"] = SyncMetadata(status="RESOLVED")

        closed_alerts = []

        def mock_close_status(
            root_cause: str, comment: str, reason: str, case_id: str, alert_id: str
        ) -> None:
            for a in alerts:
                if a.identifier == alert_id:
                    a.status = "closed"
                    closed_alerts.append(alert_id)

        job.soar_job.close_alert = mock_close_status

        job.sync_status(job_case)

        assert len(closed_alerts) == 2
        assert "alert_1" in closed_alerts

        job.soar_job.close_case.assert_called_once_with(
            root_cause="Other",
            case_id=1234,
            reason="Closed by Wiz Sync",
            comment="[SecOps & Wiz Sync Job] All alerts closed. Closing the case.",
            alert_identifier=None,
        )

    def test_modified_synced_case_ids_by_product(self) -> None:
        """Verifies that modified_synced_case_ids_by_product polls Wiz and ignores automation self-updates."""
        job = _make_job()
        job.last_run_time = 1000000
        job.processed_items = {1234: ["wiz_threat_1"]}

        updated_threat_no_comments = Issue(
            raw_data={},
            issue_id="wiz_threat_1",
            updated_at="2026-08-05T13:00:00Z",
            comments=[],
        )
        job.api_client.get_updated_threats = MagicMock(return_value=[updated_threat_no_comments])

        res = job.modified_synced_case_ids_by_product(["wiz_threat_1"], [])
        assert len(res) == 1
        assert res[0][0] == 1234

        job2 = _make_job()
        job2.last_run_time = 1785973200000
        job2.processed_items = {1234: ["wiz_threat_1"]}
        automation_comment = WizIncidentComment(
            {"id": "1", "text": "[SecOps & Wiz Sync Job] status closed...", "createdAt": "2026-08-05T13:00:00Z"}
        )
        updated_threat_self_comment = Issue(
            raw_data={},
            issue_id="wiz_threat_1",
            updated_at="2026-08-05T13:00:00Z",
            comments=[automation_comment],
        )
        job2.api_client.get_updated_threats = MagicMock(return_value=[updated_threat_self_comment])
        res2 = job2.modified_synced_case_ids_by_product(["wiz_threat_1"], [])
        assert len(res2) == 0

    @patch("wiz.jobs.wiz_secops_bidirectional_sync_job.get_users_profile_cards_with_pagination")
    def test_sync_comments_resolves_creator_email(self, mock_get_users: MagicMock) -> None:
        """Verifies that the sync job resolves creator_user_id to email using user profiles list."""
        mock_user = MagicMock(spec=UserProfileCard)
        mock_user.user_name = "creator-uuid-123"
        mock_user.raw_data = {"email": "real_analyst@company.com"}
        mock_get_users.return_value = [mock_user]

        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1")]

        comments = [
            {
                "comment": "analyst comment on Case",
                "creator_user_id": "creator-uuid-123",
                "creator_full_name": "Some Full Name",
            }
        ]
        case = _make_mock_case(1234, alerts, comments=comments)
        job_case = JobCase(case_detail=case, modification_time=1000)

        issue_comments = []
        issue = Issue(
            raw_data={},
            issue_id="wiz_threat_1",
            comments=issue_comments,
        )
        job_case.product_ids_from_secops_alerts = {"wiz_threat_1": alerts[0]}
        job_case.add_product_incident(issue, product_key="issue_id")

        job.api_client.add_comment_to_issue = MagicMock()
        job.soar_job.fetch_case_comments = MagicMock(return_value=comments)

        job.sync_comments(job_case)

        job.api_client.add_comment_to_issue.assert_called_once()
        _, kwargs = job.api_client.add_comment_to_issue.call_args
        assert "[SecOps & Wiz Sync Job] real_analyst@company.com wrote in Google SecOps on " in kwargs["comment"]
        assert "analyst comment on Case" in kwargs["comment"]
