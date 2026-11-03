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

from datetime import datetime, timezone
import json
import os
from unittest.mock import MagicMock, patch

import pytest

from microsoft365_defender.connectors import IncidentsConnector
from microsoft365_defender.connectors.IncidentsConnector import main
from microsoft365_defender.core.constants import API_ROOT, GRAPH_API_ROOT_DEFAULT, LOGIN_API_ROOT_DEFAULT
from microsoft365_defender.core.datamodels import AlertWithEvidence, Incident
from microsoft365_defender.core.Microsoft365DefenderParser import Microsoft365DefenderParser

_INCIDENTS_CONNECTOR_PATH = "microsoft365_defender.connectors.IncidentsConnector"


@pytest.fixture
def mock_siemplify():
    """Mock SiemplifyConnectorExecution instance."""
    with patch(f"{_INCIDENTS_CONNECTOR_PATH}.SiemplifyConnectorExecution") as mock_exec:
        siemplify_instance = MagicMock()
        siemplify_instance.fetch_timestamp.return_value = datetime.now(timezone.utc)
        siemplify_instance.whitelist = []
        mock_exec.return_value = siemplify_instance
        yield siemplify_instance


def test_incidents_connector_connectordef_has_api_root_parameter():
    """
    Test that IncidentsConnector.connectordef defines the 'API Root' parameter.
    """
    connectordef_path = os.path.join(
        os.path.dirname(__file__),
        "../../../Integrations/Microsoft365Defender/Connectors/IncidentsConnector.yaml",
    )
    with open(connectordef_path, "r") as f:
        data = json.load(f)

    parameters = data.get("Parameters", [])
    api_root_param = next((p for p in parameters if p.get("Name") == "API Root"), None)

    assert (
        api_root_param is not None
    ), "API Root' parameter is missing in IncidentsConnector.yaml"
    assert api_root_param.get("DefaultValue") == "https://api.security.microsoft.com"
    assert api_root_param.get("IsMandatory") is True


def test_incidents_connector_gcc_high_configuration():
    """
    Test that IncidentsConnector extracts custom GCC High API Root and passes it to Microsoft365DefenderManager.
    """
    with patch(f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param") as mock_extract_param, patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence", return_value=None
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value={}
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls, patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.SiemplifyConnectorExecution"
    ):

        mock_extract_param.side_effect = lambda siemplify, param_name, **kwargs: {
            "Login API Root": "https://login.microsoftonline.us",
            "Graph API Root": "https://graph.microsoft.us",
            "API Root": "https://api.security.microsoft.us",
            "Tenant ID": "gcc-tenant-id",
            "Client ID": "gcc-client-id",
            "Client Secret": "gcc-secret",
            "Verify SSL": False,
            "PythonProcessTimeout": 180,
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Disable Alert Tracking": False,
            "Dynamic List Field": "Incident Name",
        }.get(param_name, kwargs.get("default_value"))

        mock_manager_instance = MagicMock()
        mock_manager_instance.get_incidents.return_value = []
        mock_manager_cls.return_value = mock_manager_instance

        try:
            IncidentsConnector.main(is_test_run=True)
        except Exception:
            pass

        assert (
            mock_manager_cls.called
        ), "Microsoft365DefenderManager was not instantiated"
        call_kwargs = mock_manager_cls.call_args[1]

        assert call_kwargs.get("api_root") == "https://api.security.microsoft.us"
        assert call_kwargs.get("login_api_root") == "https://login.microsoftonline.us"
        assert call_kwargs.get("microsoft_graph_url") == "https://graph.microsoft.us"
        assert call_kwargs.get("verify_ssl") is False


def test_incidents_connector_commercial_default_configuration():
    """
    Test that IncidentsConnector uses commercial default roots when defaults are passed.
    """
    with patch(f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param") as mock_extract_param, patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence", return_value=None
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value={}
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls, patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.SiemplifyConnectorExecution"
    ):

        mock_extract_param.side_effect = lambda siemplify, param_name, **kwargs: {
            "Login API Root": LOGIN_API_ROOT_DEFAULT,
            "Graph API Root": GRAPH_API_ROOT_DEFAULT,
            "API Root": API_ROOT,
            "Tenant ID": "comm-tenant-id",
            "Client ID": "comm-client-id",
            "Client Secret": "comm-secret",
            "Verify SSL": True,
            "PythonProcessTimeout": 180,
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Disable Alert Tracking": False,
            "Dynamic List Field": "Incident Name",
        }.get(param_name, kwargs.get("default_value"))

        mock_manager_instance = MagicMock()
        mock_manager_instance.get_incidents.return_value = []
        mock_manager_cls.return_value = mock_manager_instance

        try:
            IncidentsConnector.main(is_test_run=True)
        except Exception:
            pass

        assert (
            mock_manager_cls.called
        ), "Microsoft365DefenderManager was not instantiated"
        call_kwargs = mock_manager_cls.call_args[1]

        assert call_kwargs.get("api_root") == "https://api.security.microsoft.com"
        assert (
            call_kwargs.get("login_api_root") == "https://login.microsoftonline.com"
        )
        assert call_kwargs.get("microsoft_graph_url") == "https://graph.microsoft.com"
        assert call_kwargs.get("verify_ssl") is True


def test_incidents_connector_param_extraction_and_manager_call(mock_siemplify):
    """Test that IncidentsConnector extracts assignee and tags parameters."""

    def mock_extract_connector_param(siemplify, param_name, **kwargs):
        params = {
            "Login API Root": "https://login.microsoftonline.com",
            "Graph API Root": "https://graph.microsoft.com",
            "Tenant ID": "tenant_123",
            "Client ID": "client_123",
            "Client Secret": "secret_123",
            "Verify SSL": True,
            "Environment Field Name": "",
            "Environment Regex Pattern": ".*",
            "PythonProcessTimeout": 180,
            "Lowest Severity To Fetch": "Informational",
            "Dynamic List Field": "Incident Name",
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Alert Detection Source Filter": "",
            "Alert Service Source Filter": "",
            "Incident Assignee Filter": "assignee1@test.com, assignee2@test.com",
            "Incident Tags Filter": "tag1, tag2",
            "Lowest Alert Severity To Fetch": "Informational",
            "Disable Alert Tracking": False,
        }
        return params.get(param_name, kwargs.get("default_value", ""))

    with patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param",
        side_effect=mock_extract_connector_param,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value={}
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence",
        return_value=None,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls:
        mock_manager = MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.too_many_request_last_occurrence = None
        mock_manager.get_incidents.return_value = []

        main(is_test_run=True)

        mock_manager.get_incidents.assert_called_once()
        _, kwargs = mock_manager.get_incidents.call_args
        assert kwargs["assignees"] == ["assignee1@test.com", "assignee2@test.com"]
        assert kwargs["tags"] == ["tag1", "tag2"]


def test_incidents_connector_processed_cases_structure(mock_siemplify):
    """Test that IncidentsConnector creates proper events for AlertWithEvidence."""

    def mock_extract_connector_param(siemplify, param_name, **kwargs):
        params = {
            "Login API Root": "https://login.microsoftonline.com",
            "Graph API Root": "https://graph.microsoft.com",
            "Tenant ID": "tenant_123",
            "Client ID": "client_123",
            "Client Secret": "secret_123",
            "Verify SSL": True,
            "Environment Field Name": "",
            "Environment Regex Pattern": ".*",
            "PythonProcessTimeout": 180,
            "Lowest Severity To Fetch": "Informational",
            "Dynamic List Field": "Incident Name",
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Alert Detection Source Filter": "",
            "Alert Service Source Filter": "",
            "Incident Assignee Filter": "",
            "Incident Tags Filter": "",
            "Lowest Alert Severity To Fetch": "Informational",
            "Disable Alert Tracking": False,
        }
        return params.get(param_name, kwargs.get("default_value", ""))

    raw_alert = {
        "id": "alert_100",
        "incidentId": "inc_200",
        "title": "Suspicious Activity",
        "severity": "medium",
        "assignedTo": "user@test.com",
        "firstActivityDateTime": "2023-01-01T00:00:00Z",
        "lastActivityDateTime": "2023-01-01T01:00:00Z",
        "description": "Suspicious activity detected",
        "additionalData": {
            "Query": "DeviceFileEvents",
            "DisallowedKey": "bad_val",
        },
    }
    evidences = [
        {
            "mdeDeviceId": "dev_1",
            "createdDateTime": "2023-01-01T00:10:00Z",
            "additionalData": {"noisy_key": "noisy_val"},
        }
    ]
    alert_obj = AlertWithEvidence(
        raw_data=raw_alert,
        alert_id="alert_100",
        incident_id="inc_200",
        title="Suspicious Activity",
        severity="medium",
        assignee="user@test.com",
        first_activity="2023-01-01T00:00:00Z",
        last_activity="2023-01-01T01:00:00Z",
        description="Suspicious activity detected",
        evidences=evidences,
    )

    incident_obj = Incident(
        raw_data={
            "id": "inc_200",
            "displayName": "Incident 200",
            "severity": "medium",
            "createdDateTime": "2023-01-01T00:00:00Z",
            "lastUpdateDateTime": "2023-01-01T01:00:00Z",
        },
        incident_id="inc_200",
        incident_name="Incident 200",
        severity="medium",
        classification="Unknown",
        created_time="2023-01-01T00:00:00Z",
        last_update_time="2023-01-01T01:00:00Z",
        alerts=[alert_obj],
    )

    with patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param",
        side_effect=mock_extract_connector_param,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value={}
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence",
        return_value=None,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls:
        mock_manager = MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.too_many_request_last_occurrence = None
        mock_manager.get_incidents.return_value = [incident_obj]

        main(is_test_run=True)

        mock_siemplify.return_package.assert_called_once()
        processed_alerts = mock_siemplify.return_package.call_args[0][0]
        assert len(processed_alerts) == 1
        events = processed_alerts[0].events

        assert len(events) == 3
        assert events[0]["event_type"] == "Incident"
        assert events[1]["event_type"] == "Alert"
        assert events[2]["event_type"] == "Evidence"

        assert events[1]["additionalData_Query"] == "DeviceFileEvents"
        assert "additionalData_DisallowedKey" not in events[1]
        assert "additionalData" not in events[2]
        assert "additionalData_noisy_key" not in events[2]


def test_incidents_connector_evidence_capping_500(mock_siemplify):
    """Test that IncidentsConnector caps evidences to latest 500 items."""

    def mock_extract_connector_param(siemplify, param_name, **kwargs):
        params = {
            "Login API Root": "https://login.microsoftonline.com",
            "Graph API Root": "https://graph.microsoft.com",
            "Tenant ID": "tenant_123",
            "Client ID": "client_123",
            "Client Secret": "secret_123",
            "Verify SSL": True,
            "Environment Field Name": "",
            "Environment Regex Pattern": ".*",
            "PythonProcessTimeout": 180,
            "Lowest Severity To Fetch": "Informational",
            "Dynamic List Field": "Incident Name",
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Alert Detection Source Filter": "",
            "Alert Service Source Filter": "",
            "Incident Assignee Filter": "",
            "Incident Tags Filter": "",
            "Lowest Alert Severity To Fetch": "Informational",
            "Disable Alert Tracking": False,
        }
        return params.get(param_name, kwargs.get("default_value", ""))

    raw_alert = {
        "id": "alert_600",
        "incidentId": "inc_600",
        "title": "High Evidence Volume Activity",
        "severity": "high",
        "assignedTo": "user@test.com",
        "firstActivityDateTime": "2023-01-01T00:00:00Z",
        "lastActivityDateTime": "2023-01-01T01:00:00Z",
        "description": "600 Evidences Test",
    }

    evidences = [
        {
            "mdeDeviceId": f"dev_{i}",
            "fileName": f"file_{i:03d}.exe",
            "createdDateTime": f"2023-01-01T00:{i//60:02d}:{i%60:02d}Z",
            "additionalData": {"junk": f"val_{i}"},
        }
        for i in range(600)
    ]

    alert_obj = AlertWithEvidence(
        raw_data=raw_alert,
        alert_id="alert_600",
        incident_id="inc_600",
        title="High Evidence Volume Activity",
        severity="high",
        assignee="user@test.com",
        first_activity="2023-01-01T00:00:00Z",
        last_activity="2023-01-01T01:00:00Z",
        description="600 Evidences Test",
        evidences=evidences,
    )

    incident_obj = Incident(
        raw_data={
            "id": "inc_600",
            "displayName": "Incident 600",
            "severity": "high",
            "createdDateTime": "2023-01-01T00:00:00Z",
            "lastUpdateDateTime": "2023-01-01T01:00:00Z",
        },
        incident_id="inc_600",
        incident_name="Incident 600",
        severity="high",
        classification="Unknown",
        created_time="2023-01-01T00:00:00Z",
        last_update_time="2023-01-01T01:00:00Z",
        alerts=[alert_obj],
    )

    with patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param",
        side_effect=mock_extract_connector_param,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value={}
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence",
        return_value=None,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls:
        mock_manager = MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.too_many_request_last_occurrence = None
        mock_manager.get_incidents.return_value = [incident_obj]

        main(is_test_run=True)

        mock_siemplify.return_package.assert_called_once()
        processed_alerts = mock_siemplify.return_package.call_args[0][0]
        assert len(processed_alerts) == 1
        events = processed_alerts[0].events

        assert len(events) == 502
        assert events[0]["event_type"] == "Incident"
        assert events[1]["event_type"] == "Alert"

        evidence_events = events[2:]
        assert len(evidence_events) == 500
        for ev_evt in evidence_events:
            assert ev_evt["event_type"] == "Evidence"

        assert "additionalData" not in events[1]
        assert "additionalData" not in events[2]


def test_alert_with_evidence_hash_changes_with_new_evidence_or_assets():
    """Test that new evidence or assets change to_hash() result so updated alert is re-ingested."""
    raw_alert_1 = {
        "id": "alert_hash_test",
        "incidentId": "inc_hash_test",
        "title": "Malware Detected",
        "severity": "high",
        "serviceSource": "microsoftDefenderForEndpoint",
        "evidence": [
            {"mdeDeviceId": "dev_1", "verdict": "malicious"}
        ],
        "assets": [
            {"assetId": "asset_1"}
        ]
    }
    raw_alert_2 = {
        "id": "alert_hash_test",
        "incidentId": "inc_hash_test",
        "title": "Malware Detected",
        "severity": "high",
        "serviceSource": "microsoftDefenderForEndpoint",
        "evidence": [
            {"mdeDeviceId": "dev_1", "verdict": "malicious"},
            {"mdeDeviceId": "dev_2", "verdict": "clean"}
        ],
        "assets": [
            {"assetId": "asset_1"},
            {"assetId": "asset_2"}
        ]
    }

    alert_1 = AlertWithEvidence(
        raw_data=raw_alert_1,
        alert_id="alert_hash_test",
        incident_id="inc_hash_test",
        title="Malware Detected",
        severity="high",
        assignee=None,
        first_activity="2023-01-01T00:00:00Z",
        last_activity="2023-01-01T00:00:00Z",
        description="Test",
        evidences=raw_alert_1["evidence"],
    )
    alert_2 = AlertWithEvidence(
        raw_data=raw_alert_2,
        alert_id="alert_hash_test",
        incident_id="inc_hash_test",
        title="Malware Detected",
        severity="high",
        assignee=None,
        first_activity="2023-01-01T00:00:00Z",
        last_activity="2023-01-01T00:00:00Z",
        description="Test",
        evidences=raw_alert_2["evidence"],
    )

    assert alert_1.to_hash() != alert_2.to_hash()
    assert alert_1.alert_unique_id != alert_2.alert_unique_id
    assert "evidence" in alert_1.to_json()
    assert "assets" in alert_1.to_json()

    events_1 = alert_1.create_events({"event_type": "Incident"})
    alert_event = events_1[1]
    assert alert_event["event_type"] == "Alert"
    assert "evidence_1_mdeDeviceId" in alert_event
    assert alert_event["assets_1_assetId"] == "asset_1"


def test_alert_with_evidence_hash_changes_with_asset_only_update():
    """Test that modifying assets only (with unchanged evidence) via parser changes the alert hash."""
    parser = Microsoft365DefenderParser()
    raw_alert_initial = {
        "id": "alert_asset_test",
        "incidentId": "inc_asset_test",
        "title": "Suspicious Activity",
        "severity": "medium",
        "evidence": [
            {"mdeDeviceId": "dev_1", "verdict": "malicious"}
        ],
        "assets": [
            {"assetId": "asset_1"}
        ],
    }
    raw_alert_updated_assets = {
        "id": "alert_asset_test",
        "incidentId": "inc_asset_test",
        "title": "Suspicious Activity",
        "severity": "medium",
        "evidence": [
            {"mdeDeviceId": "dev_1", "verdict": "malicious"}
        ],
        "assets": [
            {"assetId": "asset_1"},
            {"assetId": "asset_2"}
        ],
    }

    alert_initial = parser.build_alert_with_evidence_object(raw_alert_initial)
    alert_updated = parser.build_alert_with_evidence_object(raw_alert_updated_assets)

    assert alert_initial.to_hash() != alert_updated.to_hash()
    assert alert_initial.alert_unique_id != alert_updated.alert_unique_id


def test_alert_with_evidence_hash_ignores_fields_in_ignore_list_and_time_fields():
    """Test that updating ignored fields or time fields does not change the alert hash."""
    raw_alert_initial = {
        "id": "alert_ignore_test",
        "incidentId": "inc_ignore_test",
        "title": "Initial Title",
        "severity": "medium",
        "status": "new",
        "assignedTo": "admin@domain.com",
        "category": "InitialCategory",
        "categories": ["InitialCategory"],
        "investigationState": "queued",
        "recommendedActions": "Investigate host",
        "alertWebUrl": "https://security.microsoft.com/alerts/1",
        "incidentWebUrl": "https://security.microsoft.com/incidents/1",
        "lastUpdateDateTime": "2026-08-13T10:00:00Z",
        "lastActivityDateTime": "2026-08-13T10:00:00Z",
        "firstActivityDateTime": "2026-08-13T09:00:00Z",
        "createdDateTime": "2026-08-13T09:00:00Z",
        "description": "Original description",
        "evidence": [
            {"mdeDeviceId": "dev_1", "verdict": "malicious"}
        ]
    }

    raw_alert_updated_ignored = {
        "id": "alert_ignore_test",
        "incidentId": "inc_ignore_test",
        "title": "Updated Title",
        "severity": "high",
        "status": "resolved",
        "assignedTo": "analyst@domain.com",
        "category": "UpdatedCategory",
        "categories": ["UpdatedCategory"],
        "investigationState": "completed",
        "recommendedActions": "No action needed",
        "alertWebUrl": "https://security.microsoft.com/alerts/1_updated",
        "incidentWebUrl": "https://security.microsoft.com/incidents/1_updated",
        "lastUpdateDateTime": "2026-08-13T11:00:00Z",
        "lastActivityDateTime": "2026-08-13T11:00:00Z",
        "firstActivityDateTime": "2026-08-13T09:00:00Z",
        "createdDateTime": "2026-08-13T09:00:00Z",
        "description": "Original description",
        "evidence": [
            {"mdeDeviceId": "dev_1", "verdict": "malicious"}
        ]
    }

    alert_initial = AlertWithEvidence(
        raw_data=raw_alert_initial,
        alert_id="alert_ignore_test",
        incident_id="inc_ignore_test",
        title="Initial Title",
        severity="medium",
        assignee="admin@domain.com",
        first_activity="2026-08-13T09:00:00Z",
        last_activity="2026-08-13T10:00:00Z",
        description="Original description",
        evidences=raw_alert_initial["evidence"],
    )

    alert_updated_ignored = AlertWithEvidence(
        raw_data=raw_alert_updated_ignored,
        alert_id="alert_ignore_test",
        incident_id="inc_ignore_test",
        title="Updated Title",
        severity="high",
        assignee="analyst@domain.com",
        first_activity="2026-08-13T09:00:00Z",
        last_activity="2026-08-13T11:00:00Z",
        description="Original description",
        evidences=raw_alert_updated_ignored["evidence"],
    )

    assert alert_initial.to_hash() == alert_updated_ignored.to_hash()
    assert alert_initial.alert_unique_id == alert_updated_ignored.alert_unique_id


def test_incidents_connector_padding_time_applied():
    """Test that IncidentsConnector applies 5 minutes padding to start_time."""
    from datetime import timedelta
    from microsoft365_defender.core.constants import PADDING_PERIOD_IN_MINUTES

    assert PADDING_PERIOD_IN_MINUTES == 5

    with patch(f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param") as mock_extract_param, patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence", return_value=None
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value={}
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls, patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.SiemplifyConnectorExecution"
    ) as mock_siemplify_cls, patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.get_last_success_time"
    ) as mock_get_last_success_time:

        fixed_last_success_time = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
        mock_get_last_success_time.return_value = fixed_last_success_time

        mock_extract_param.side_effect = lambda siemplify, param_name, **kwargs: {
            "Login API Root": LOGIN_API_ROOT_DEFAULT,
            "Graph API Root": GRAPH_API_ROOT_DEFAULT,
            "API Root": API_ROOT,
            "Tenant ID": "tenant",
            "Client ID": "client",
            "Client Secret": "secret",
            "Verify SSL": True,
            "PythonProcessTimeout": 180,
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Disable Alert Tracking": False,
            "Dynamic List Field": "Incident Name",
        }.get(param_name, kwargs.get("default_value"))

        mock_manager_instance = MagicMock()
        mock_manager_instance.get_incidents.return_value = []
        mock_manager_cls.return_value = mock_manager_instance

        IncidentsConnector.main(is_test_run=True)

        assert mock_manager_instance.get_incidents.called
        call_kwargs = mock_manager_instance.get_incidents.call_args[1]

        expected_start_time = fixed_last_success_time - timedelta(minutes=5)
        assert call_kwargs.get("start_time") == expected_start_time


def test_incidents_connector_no_duplicate_alerts_in_padding_window():
    """Test that existing alerts fetched within padding window are filtered out and not duplicated."""
    raw_incident = {
        "incidentId": "inc_pad_1",
        "incidentName": "Test Incident",
        "severity": "high",
        "lastUpdateDateTime": "2026-08-20T12:00:00Z",
    }
    raw_alert = {
        "id": "alert_pad_1",
        "incidentId": "inc_pad_1",
        "title": "Alert 1",
        "severity": "high",
        "evidence": [{"mdeDeviceId": "dev_1"}]
    }
    incident = Incident(
        raw_data=raw_incident,
        incident_id="inc_pad_1",
        incident_name="Test Incident",
        severity="high",
        classification="truePositive",
        created_time="2026-08-20T11:00:00Z",
        last_update_time="2026-08-20T12:00:00Z",
        alerts=[],
    )
    alert = AlertWithEvidence(
        raw_data=raw_alert,
        alert_id="alert_pad_1",
        incident_id="inc_pad_1",
        title="Alert 1",
        severity="high",
        assignee=None,
        first_activity="2026-08-20T11:00:00Z",
        last_activity="2026-08-20T11:00:00Z",
        description="Desc",
        evidences=raw_alert["evidence"],
    )

    # Already seen alert unique ID in existing_incidents
    existing_incidents = {"inc_pad_1": [alert.alert_unique_id]}

    with patch(f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param") as mock_extract_param, patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence", return_value=None
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value=existing_incidents
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls, patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.SiemplifyConnectorExecution"
    ) as mock_siemplify_cls:

        mock_siemplify = MagicMock()
        mock_siemplify_cls.return_value = mock_siemplify

        mock_extract_param.side_effect = lambda siemplify, param_name, **kwargs: {
            "Login API Root": LOGIN_API_ROOT_DEFAULT,
            "Graph API Root": GRAPH_API_ROOT_DEFAULT,
            "API Root": API_ROOT,
            "Tenant ID": "tenant",
            "Client ID": "client",
            "Client Secret": "secret",
            "Verify SSL": True,
            "PythonProcessTimeout": 180,
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Disable Alert Tracking": False,
            "Dynamic List Field": "Incident Name",
        }.get(param_name, kwargs.get("default_value"))

        mock_manager_instance = MagicMock()
        # Incident with empty alerts (because all were filtered out) should not be returned by get_incidents
        mock_manager_instance.get_incidents.return_value = []
        mock_manager_cls.return_value = mock_manager_instance

        IncidentsConnector.main(is_test_run=False)

        assert mock_siemplify.return_package.called
        processed_alerts = mock_siemplify.return_package.call_args[0][0]
        assert len(processed_alerts) == 0

def test_incidents_connector_passes_python_process_timeout_and_starting_time(mock_siemplify):
    """Test that IncidentsConnector passes script_timeout and connector_starting_time to get_incidents."""
    def mock_extract_connector_param(siemplify, param_name, **kwargs):
        params = {
            "Login API Root": LOGIN_API_ROOT_DEFAULT,
            "Graph API Root": GRAPH_API_ROOT_DEFAULT,
            "API Root": API_ROOT,
            "Tenant ID": "tenant_123",
            "Client ID": "client_123",
            "Client Secret": "secret_123",
            "Verify SSL": True,
            "PythonProcessTimeout": 300,
            "Lowest Severity To Fetch": "Informational",
            "Dynamic List Field": "Incident Name",
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Disable Alert Tracking": False,
        }
        return params.get(param_name, kwargs.get("default_value", ""))

    with patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param",
        side_effect=mock_extract_connector_param,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value={}
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence", return_value=None
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.connector_starting_time", 1700000000000
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls:
        mock_manager = MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.too_many_request_last_occurrence = None
        mock_manager.get_incidents.return_value = []

        main(is_test_run=True)

        mock_manager.get_incidents.assert_called_once()
        call_kwargs = mock_manager.get_incidents.call_args[1]
        assert call_kwargs.get("python_process_timeout") == 300
        assert call_kwargs.get("connector_starting_time") == 1700000000000


def test_incidents_connector_approaching_timeout_stops_processing_incidents(mock_siemplify):
    """Test that IncidentsConnector gracefully exits incident iteration when approaching timeout."""
    def mock_extract_connector_param(siemplify, param_name, **kwargs):
        params = {
            "Login API Root": LOGIN_API_ROOT_DEFAULT,
            "Graph API Root": GRAPH_API_ROOT_DEFAULT,
            "API Root": API_ROOT,
            "Tenant ID": "tenant_123",
            "Client ID": "client_123",
            "Client Secret": "secret_123",
            "Verify SSL": True,
            "PythonProcessTimeout": 180,
            "Lowest Severity To Fetch": "Informational",
            "Dynamic List Field": "Incident Name",
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Disable Alert Tracking": False,
        }
        return params.get(param_name, kwargs.get("default_value", ""))

    incidents = [
        Incident(
            raw_data={
                "id": f"inc_{i}",
                "displayName": f"Incident {i}",
                "severity": "medium",
                "createdDateTime": "2023-01-01T00:00:00Z",
                "lastUpdateDateTime": "2023-01-01T01:00:00Z",
            },
            incident_id=f"inc_{i}",
            incident_name=f"Incident {i}",
            severity="medium",
            classification="Unknown",
            created_time="2023-01-01T00:00:00Z",
            last_update_time="2023-01-01T01:00:00Z",
            alerts=[],
        )
        for i in range(5)
    ]

    with patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param",
        side_effect=mock_extract_connector_param,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value={}
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence", return_value=None
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.is_approaching_timeout", side_effect=[False, False, True]
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls:
        mock_manager = MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.too_many_request_last_occurrence = None
        mock_manager.get_incidents.return_value = incidents

        main(is_test_run=False)

        mock_siemplify.return_package.assert_called_once()
        processed_alerts = mock_siemplify.return_package.call_args[0][0]
        # Only 2 incidents should have been processed before timeout triggered
        assert len(processed_alerts) == 2
        mock_siemplify.LOGGER.info.assert_any_call(
            "Timeout is approaching. Connector will gracefully exit"
        )


@pytest.mark.parametrize("timeout_val", [60, 120, 600])
def test_incidents_connector_passes_custom_script_timeouts(mock_siemplify, timeout_val):
    """Test that IncidentsConnector passes various configured PythonProcessTimeout values."""
    def mock_extract_connector_param(siemplify, param_name, **kwargs):
        params = {
            "Login API Root": LOGIN_API_ROOT_DEFAULT,
            "Graph API Root": GRAPH_API_ROOT_DEFAULT,
            "API Root": API_ROOT,
            "Tenant ID": "tenant_123",
            "Client ID": "client_123",
            "Client Secret": "secret_123",
            "Verify SSL": True,
            "PythonProcessTimeout": timeout_val,
            "Lowest Severity To Fetch": "Informational",
            "Dynamic List Field": "Incident Name",
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Disable Alert Tracking": False,
        }
        return params.get(param_name, kwargs.get("default_value", ""))

    with patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param",
        side_effect=mock_extract_connector_param,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value={}
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence", return_value=None
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls:
        mock_manager = MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.too_many_request_last_occurrence = None
        mock_manager.get_incidents.return_value = []

        main(is_test_run=True)

        mock_manager.get_incidents.assert_called_once()
        call_kwargs = mock_manager.get_incidents.call_args[1]
        assert call_kwargs.get("python_process_timeout") == timeout_val


def test_incidents_connector_does_not_advance_timestamp_on_too_many_requests(mock_siemplify):
    """Test that timestamp is not advanced when 0 incidents fetched due to TooManyRequests error."""

    def mock_extract_param(siemplify, param_name, **kwargs):
        return {
            "Login API Root": LOGIN_API_ROOT_DEFAULT,
            "Graph API Root": GRAPH_API_ROOT_DEFAULT,
            "API Root": API_ROOT,
            "Tenant ID": "tenant",
            "Client ID": "client",
            "Client Secret": "secret",
            "Verify SSL": True,
            "PythonProcessTimeout": 180,
            "Max Hours Backwards": 1,
            "Max Incidents To Fetch": 10,
            "Use whitelist as a blacklist": False,
            "Disable Overflow": True,
            "Incident Status Filter": "Active, In Progress",
            "Disable Alert Tracking": False,
            "Dynamic List Field": "Incident Name",
        }.get(param_name, kwargs.get("default_value"))

    with patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.extract_connector_param",
        side_effect=mock_extract_param,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_existing_incidents", return_value={}
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.read_last_too_many_requests_occurrence",
        return_value=None,
    ), patch(
        f"{_INCIDENTS_CONNECTOR_PATH}.Microsoft365DefenderManager"
    ) as mock_manager_cls:
        mock_manager = MagicMock()
        mock_manager_cls.return_value = mock_manager
        mock_manager.too_many_request_last_occurrence = 1787684039000
        mock_manager.get_incidents.return_value = []

        IncidentsConnector.main(is_test_run=False)

        mock_siemplify.save_timestamp.assert_not_called()
