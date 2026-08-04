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

from unittest.mock import MagicMock, PropertyMock, patch

import json
import pytest
from TIPCommon.base.job.job_case import JobCase, SyncMetadata
from TIPCommon.data_models import AlertCard, CaseDataStatus, CaseDetails

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

        with patch("secret_manager.core.action_init" if False else "wiz.core.action_init.create_api_client") as mock_create_client:
            job._init_api_clients()
            assert job.sync_status_enabled is True
            assert job.sync_comments_enabled is True
            assert job.sync_product_link_enabled is False
            assert job.sync_severity_enabled is False

    def test_extract_product_ids_from_case(self) -> None:
        """Verifies that Wiz Threat IDs are extracted from SOAR alert_group_identifier."""
        job = _make_job()
        alerts = [
            _make_mock_alert("alert_1", "wiz_threat_1"),
            _make_mock_alert("alert_2", "wiz_threat_2"),
            _make_mock_alert("alert_3", None),  # Non-Wiz alert
            _make_mock_alert("alert_4", "wiz_threat_1"),  # Duplicate
        ]
        case = _make_mock_case(1234, alerts)
        job_case = JobCase(case_detail=case, modification_time=1000)

        threat_ids = job._extract_product_ids_from_case(job_case)
        assert threat_ids == ["wiz_threat_1", "wiz_threat_2"]

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

        # Mock soar_job.close_alert to update the alert status to closed
        def mock_close_status(root_cause, comment, reason, case_id, alert_id):
            alerts[0].status = "closed"

        job.soar_job.close_alert = mock_close_status

        job.sync_status(job_case)

        # Overall case must be closed because all alerts are closed
        job.soar_job.close_case.assert_called_once_with(
            root_cause="Other",
            case_id=1234,
            reason="Closed by Wiz Sync",
            comment="[SecOps & Wiz Sync Job] All alerts closed. Closing the case.",
            alert_identifier=None,
        )

    def test_sync_status_inbound_mixed_alerts_leaves_case_open(self) -> None:
        """Verifies that RESOLVED Wiz Threat closes Wiz alerts but leaves the case open if active non-Wiz alerts exist."""
        job = _make_job()
        alerts = [
            _make_mock_alert("alert_1", "wiz_threat_1", status="open"),
            _make_mock_alert("alert_2", None, status="open"),  # Active non-Wiz alert
        ]
        case = _make_mock_case(1234, alerts)
        job_case = JobCase(case_detail=case, modification_time=1000)
        job_case.product_ids_from_secops_alerts = {"wiz_threat_1": alerts[0]}
        job_case.alert_metadata["alert_1"] = SyncMetadata(status="RESOLVED")

        # Mock soar_job.close_alert to update the alert status to closed
        def mock_close_status(root_cause, comment, reason, case_id, alert_id):
            alerts[0].status = "closed"

        job.soar_job.close_alert = mock_close_status

        job.sync_status(job_case)

        # Case should NOT be closed
        job.soar_job.close_case.assert_not_called()

        # Audit comment explaining mixed alerts must be added
        job.soar_job.add_comment.assert_called_once()
        args, kwargs = job.soar_job.add_comment.call_args
        assert kwargs["case_id"] == 1234
        assert "Mixed Alert Resolution" in kwargs["comment"]

    def test_sync_status_outbound_case_closed_resolved_malicious(self) -> None:
        """Verifies that closing a case as malicious in SecOps resolves the Wiz threat as MALICIOUS_THREAT."""
        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1")]
        case = _make_mock_case(1234, alerts, status=CaseDataStatus.CLOSED, close_reason="REASON_MALICIOUS")
        job_case = JobCase(case_detail=case, modification_time=1000)
        job_case.product_ids_from_secops_alerts = {"wiz_threat_1": alerts[0]}
        job_case.alert_metadata["alert_1"] = SyncMetadata(status="OPEN")

        job.sync_status(job_case)

        # Must call resolve_issue with Malicious Threat
        job.api_client.resolve_issue.assert_called_once_with(
            issue_id="wiz_threat_1",
            resolution_reason="Malicious Threat",
            resolution_note="Closed via SecOps Case Sync",
        )

    def test_sync_status_outbound_case_closed_false_positive(self) -> None:
        """Verifies that closing a case as false positive in SecOps rejects the Wiz threat with FALSE_POSITIVE."""
        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1")]
        case = _make_mock_case(1234, alerts, status=CaseDataStatus.CLOSED, close_reason="REASON_NOT_MALICIOUS")
        job_case = JobCase(case_detail=case, modification_time=1000)
        job_case.product_ids_from_secops_alerts = {"wiz_threat_1": alerts[0]}
        job_case.alert_metadata["alert_1"] = SyncMetadata(status="OPEN")

        job.sync_status(job_case)

        # Must call ignore_issue with False Positive (status REJECTED)
        job.api_client.ignore_issue.assert_called_once_with(
            issue_id="wiz_threat_1",
            resolution_reason="False Positive",
            note="Closed via SecOps Case Sync",
        )

    def test_sync_severity_escalates_priority(self) -> None:
        """Verifies that Wiz Threat severity CRITICAL escalates a SOAR case priority from Medium to Critical."""
        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1", priority="Medium")]
        case = _make_mock_case(1234, alerts)
        job_case = JobCase(case_detail=case, modification_time=1000)
        job_case.alert_metadata["alert_1"] = SyncMetadata(severity="CRITICAL")

        job.sync_severity_to_case = MagicMock()

        job.sync_severity(job_case)

        # Must escalate priority to Critical
        job.sync_severity_to_case.assert_called_once_with(
            alert_identifier="alert_1",
            alert_name="Wiz Alert",
            case_id="1234",
            new_priority="Critical",
        )
        # Verify comment is added
        job.soar_job.add_comment.assert_called_once()
        assert "Severity Escalation" in job.soar_job.add_comment.call_args[1]["comment"]

    def test_sync_severity_does_not_downgrade_priority(self) -> None:
        """Verifies that Wiz Threat severity MEDIUM does not downgrade a SOAR case priority from High to Medium."""
        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1", priority="High")]
        case = _make_mock_case(1234, alerts)
        job_case = JobCase(case_detail=case, modification_time=1000)
        job_case.alert_metadata["alert_1"] = SyncMetadata(severity="MEDIUM")

        job.sync_severity_to_case = MagicMock()

        job.sync_severity(job_case)

        # Must NOT call sync_severity_to_case
        job.sync_severity_to_case.assert_not_called()
        job.soar_job.add_comment.assert_not_called()

    def test_sync_comments_loop_back_prevention(self) -> None:
        """Verifies that sync comments ignores loopback comments originating from sync job."""
        job = _make_job()
        alerts = [_make_mock_alert("alert_1", "wiz_threat_1")]
        # Mock comments in SecOps case details
        comments = [
            {"comment": "[Wiz Note] wiz_threat_1: note from Wiz", "creator": "sync@soar.com"},  # loopback
            {"comment": "analyst comment on Case", "creator": "analyst@company.com"},  # valid comment to sync
        ]
        case = _make_mock_case(1234, alerts, comments=comments)
        job_case = JobCase(case_detail=case, modification_time=1000)

        # Mock alert incident comments in Wiz
        issue_comments = [
            WizIncidentComment({"id": "1", "text": "[SecOps & Wiz Sync Job] user wrote: comment text"}),  # loopback
            WizIncidentComment({"id": "2", "text": "analyst comment in Wiz"}),  # valid comment to sync
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

        job.sync_comments(job_case)

        # Verify case comments to sync to Wiz:
        # only "analyst comment on Case" should be synced
        job.sync_case_comments_to_product.assert_called_once()
        synced_comments = job.sync_case_comments_to_product.call_args[1]["comments"]
        assert len(synced_comments) == 1
        assert "analyst comment on Case" in synced_comments[0]

        # Verify Wiz comments to sync to Case:
        # only "analyst comment in Wiz" should be synced
        job.sync_product_comments_to_case.assert_called_once()
        synced_wiz_comments = job.sync_product_comments_to_case.call_args[1]["comments"]
        assert len(synced_wiz_comments) == 1
        assert "analyst comment in Wiz" in synced_wiz_comments[0]

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
        def mock_close_status(root_cause, comment, reason, case_id, alert_id):
            for a in alerts:
                if a.identifier == alert_id:
                    a.status = "closed"
                    closed_alerts.append(alert_id)

        job.soar_job.close_alert = mock_close_status

        job.sync_status(job_case)

        # Both alerts should be closed
        assert len(closed_alerts) == 2
        assert "alert_1" in closed_alerts

        # Overall case must be closed because all alerts are closed
        job.soar_job.close_case.assert_called_once_with(
            root_cause="Other",
            case_id=1234,
            reason="Closed by Wiz Sync",
            comment="[SecOps & Wiz Sync Job] All alerts closed. Closing the case.",
            alert_identifier=None,
        )

