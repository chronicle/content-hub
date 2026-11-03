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
from unittest.mock import patch, MagicMock, call

import pytest

from soar_sdk.SiemplifyUtils import unix_now
from microsoft365_defender.core.datamodels import AlertWithEvidence
from microsoft365_defender.core.Microsoft365DefenderParser import Microsoft365DefenderParser
from microsoft365_defender.core.Microsoft365DefenderExceptions import (
    Microsoft365DefenderException,
    APIPermissionError,
    NotFoundItemException,
)
from microsoft365_defender.core.constants import (
    INCIDENTS_LIMIT_PER_REQUEST,
    ALERTS_LIMIT_PER_REQUEST,
)

from microsoft365_defender.core.Microsoft365DefenderManager import (
    Microsoft365DefenderManager,
)


# pylint: disable=redefined-outer-name
@pytest.fixture
def manager():
    """Prepare a Manager instance for testing."""
    with patch(
        "microsoft365_defender.core.Microsoft365DefenderManager"
        ".Microsoft365DefenderManager._generate_token",
        MagicMock(return_value="dummy-token"),
    ):
        manager_instance = Microsoft365DefenderManager(
            api_root="https://api.microsoft.com",
            client_id="client_id",
            client_secret="client_secret",
            tenant_id="tenant_id",
            verify_ssl=False,
            microsoft_graph_url="https://graph.microsoft.com",
        )
        manager_instance.session = MagicMock()

        yield manager_instance


def test_search_for_devices_api_method_is_graph(manager):
    """Test that graph API is called when api_method is equal to `graph`"""
    manager.session.post.return_value.status_code = 200
    manager.session.post.return_value.json.return_value = {"Results": []}

    with patch.object(manager.parser, "build_device_objects", return_value=[]):
        custom_query = "DeviceEvents"
        limit = 10

        expected_url = "https://graph.microsoft.com/beta/security/runHuntingQuery"
        expected_payload = {"query": f"{custom_query}| limit {limit}"}

        devices, query = manager.search_for_devices(
            custom_query=custom_query, limit=limit
        )

        assert devices == []
        assert query == expected_payload["query"]

        manager.session.post.assert_called_once_with(
            expected_url, json=expected_payload
        )


def test_search_for_devices_custom_query_with_timeframe(manager: Microsoft365DefenderManager) -> None:
    """Test that graph API is called with timestamp filtering when custom query and time bounds are provided."""
    manager.session.post.return_value.status_code = 200
    manager.session.post.return_value.json.return_value = {"Results": []}

    with patch.object(manager.parser, "build_device_objects", return_value=[]):
        custom_query: str = "DeviceEvents"
        start_time: str = "2026-10-15T00:00:00Z"
        end_time: str = "2026-10-15T12:00:00Z"
        limit: int = 10

        expected_url: str = "https://graph.microsoft.com/beta/security/runHuntingQuery"
        expected_query: str = (
            f"{custom_query}| where Timestamp between(datetime({start_time}) .. datetime({end_time}))"
            f"| limit {limit}"
        )
        expected_payload: dict[str, str] = {"query": expected_query}

        devices, query = manager.search_for_devices(
            custom_query=custom_query,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        assert devices == []
        assert query == expected_payload["query"]

        manager.session.post.assert_called_once_with(expected_url, json=expected_payload)


def test_search_for_devices_fallback(manager):
    """Test that the fallback API is called after the Graph API call fails with a
     permission error."""
    graph_api_response = MagicMock()
    graph_api_response.status_code = 403

    fallback_api_response = MagicMock()
    fallback_api_response.status_code = 200
    fallback_api_response.json.return_value = {"Results": []}

    manager.session.post.side_effect = [
        graph_api_response,
        fallback_api_response,
    ]

    with patch(
        "microsoft365_defender.core.Microsoft365DefenderManager"
        ".validate_response"
    ) as mock_validate_response:
        mock_validate_response.side_effect = [APIPermissionError, None]

        with patch.object(
            manager.parser, "build_device_objects", return_value=[]
        ):
            custom_query = "DeviceEvents"
            limit = 20

            graph_url = "https://graph.microsoft.com/beta/security/runHuntingQuery"
            graph_payload = {"query": f"{custom_query}| limit {limit}"}

            fallback_url = "https://api.microsoft.com/api/advancedhunting/run"
            fallback_payload = {"Query": f"{custom_query}| limit {limit}"}

            devices, query = manager.search_for_devices(
                custom_query=custom_query, limit=limit
            )

            assert devices == []
            assert query == graph_payload["query"]

            calls = [
                call(graph_url, json=graph_payload),
                call(fallback_url, json=fallback_payload),
            ]
            manager.session.post.assert_has_calls(calls, any_order=False)
            assert manager.session.post.call_count == 2


def test_search_for_devices_raises_exception_on_bad_request(manager):
    """Test that an exception is raised for a 400 status code."""
    manager.session.post.return_value.status_code = 400
    manager.session.post.return_value.json.return_value = {
        "error": {"message": "Invalid query"}
    }

    with pytest.raises(Microsoft365DefenderException, match="Invalid query"):
        manager.search_for_devices(custom_query="invalid query", limit=10)


def test_get_incident_success(manager):
    """Test that get_incident returns parsed Incident object on a 200 response."""
    mock_incident = MagicMock()
    manager.session.get.return_value.status_code = 200
    manager.session.get.return_value.json.return_value = {
        "id": "inc-123",
        "status": "active",
    }

    with patch.object(
        manager.parser, "build_incident_object", return_value=mock_incident
    ):
        result = manager.get_incident(incident_id="123")

        assert result is mock_incident
        manager.session.get.assert_called_once()


def test_get_incident_not_found(manager):
    """Test that get_incident raises NotFoundItemException on a 404 response."""
    manager.session.get.return_value.status_code = 404

    with pytest.raises(NotFoundItemException, match='incident "123" wasn\'t found'):
        manager.get_incident(incident_id="123")


def test_get_incident_calls_parser(manager):
    """Test that get_incident passes the JSON response to build_incident_object."""
    mock_incident = MagicMock()
    raw_response = {"id": "inc-456", "displayName": "Test Incident"}
    manager.session.get.return_value.status_code = 200
    manager.session.get.return_value.json.return_value = raw_response

    with patch.object(
        manager.parser, "build_incident_object", return_value=mock_incident
    ) as mock_build:
        manager.get_incident(incident_id="456")

        mock_build.assert_called_once_with(raw_response)


def test_alert_with_evidence_create_events():
    """Test that AlertWithEvidence creates Incident, Alert, and Evidence events."""
    raw_alert = {
        "id": "alert-1",
        "incidentId": "inc-1",
        "title": "Test Alert",
        "severity": "high",
        "assignedTo": "user@example.com",
        "firstActivityDateTime": "2023-01-01T00:00:00Z",
        "lastActivityDateTime": "2023-01-01T01:00:00Z",
        "description": "Test alert description",
        "additionalData": {
            "Query": "DeviceFileEvents",
            "Analytic Rule Name": "Rule1",
            "UnwantedKey": "should_be_removed",
        },
    }
    evidences = [
        {
            "mdeDeviceId": "dev-1",
            "createdDateTime": f"2023-01-01T00:{i:02d}:00Z",
            "additionalData": {"noisy": "data"},
        }
        for i in range(10)
    ]
    alert_obj = AlertWithEvidence(
        raw_data=raw_alert,
        alert_id="alert-1",
        incident_id="inc-1",
        title="Test Alert",
        severity="high",
        assignee="user@example.com",
        first_activity="2023-01-01T00:00:00Z",
        last_activity="2023-01-01T01:00:00Z",
        description="Test alert description",
        evidences=evidences,
    )

    incident_event = {"event_type": "Incident", "incidentId": "inc-1"}
    events = alert_obj.create_events(incident_event)

    assert len(events) == 12
    assert events[0]["event_type"] == "Incident"
    assert events[1]["event_type"] == "Alert"
    assert events[2]["event_type"] == "Evidence"
    assert events[1]["additionalData_Query"] == "DeviceFileEvents"
    assert events[1]["additionalData_Analytic Rule Name"] == "Rule1"
    assert "additionalData_UnwantedKey" not in events[1]
    assert "additionalData" not in events[2]
    assert "additionalData_noisy" not in events[2]
    assert events[2]["alert_metadata_title"] == "Test Alert"


def test_alert_additional_data_subset_keys():
    """Test that AlertWithEvidence handles subset of allowlisted additionalData keys without error."""
    raw_alert = {
        "id": "alert-subset",
        "incidentId": "inc-subset",
        "title": "Subset Keys Test",
        "severity": "medium",
        "additionalData": {
            "Query": "SecurityEvent | limit 10",
            "WorkspaceName": "myWorkspace",
            "WorkspaceId": "ws-12345",
        },
    }
    alert_obj = AlertWithEvidence(
        raw_data=raw_alert,
        alert_id="alert-subset",
        incident_id="inc-subset",
        title="Subset Keys Test",
        severity="medium",
        assignee="user@example.com",
        first_activity="2023-01-01T00:00:00Z",
        last_activity="2023-01-01T01:00:00Z",
        description="Subset test description",
        evidences=[],
    )

    incident_event = {"event_type": "Incident", "incidentId": "inc-subset"}
    events = alert_obj.create_events(incident_event)

    assert len(events) == 2
    assert events[1]["event_type"] == "Alert"
    assert events[1]["additionalData_Query"] == "SecurityEvent | limit 10"
    assert events[1]["additionalData_WorkspaceName"] == "myWorkspace"
    assert events[1]["additionalData_WorkspaceId"] == "ws-12345"


def test_alert_additional_data_no_allowed_keys():
    """Test that AlertWithEvidence handles additionalData with no allowlisted keys safely."""
    raw_alert = {
        "id": "alert-mde",
        "incidentId": "inc-mde",
        "title": "MDE Alert Test",
        "severity": "low",
        "additionalData": {
            "MachineId": "mde-machine-001",
            "ProcessCommandLine": "cmd.exe /c calc.exe",
            "DetectorId": "det-999",
        },
    }
    alert_obj = AlertWithEvidence(
        raw_data=raw_alert,
        alert_id="alert-mde",
        incident_id="inc-mde",
        title="MDE Alert Test",
        severity="low",
        assignee="user@example.com",
        first_activity="2023-01-01T00:00:00Z",
        last_activity="2023-01-01T01:00:00Z",
        description="MDE alert test",
        evidences=[],
    )

    incident_event = {"event_type": "Incident", "incidentId": "inc-mde"}
    events = alert_obj.create_events(incident_event)

    assert len(events) == 2
    assert events[1]["event_type"] == "Alert"
    assert "additionalData" not in events[1]
    assert "additionalData_MachineId" not in events[1]


def test_alert_additional_data_missing_or_none():
    """Test that AlertWithEvidence handles missing or None additionalData safely."""
    raw_alert = {
        "id": "alert-none",
        "incidentId": "inc-none",
        "title": "None additionalData Test",
        "severity": "low",
        "additionalData": None,
    }
    alert_obj = AlertWithEvidence(
        raw_data=raw_alert,
        alert_id="alert-none",
        incident_id="inc-none",
        title="None additionalData Test",
        severity="low",
        assignee="user@example.com",
        first_activity="2023-01-01T00:00:00Z",
        last_activity="2023-01-01T01:00:00Z",
        description="None additionalData test",
        evidences=[],
    )

    incident_event = {"event_type": "Incident", "incidentId": "inc-none"}
    events = alert_obj.create_events(incident_event)

    assert len(events) == 2
    assert events[1]["event_type"] == "Alert"
    assert "additionalData" not in events[1]


def test_get_incidents_assignees_and_tags_filtering(manager):
    """Test get_incidents with assignees and tags filtering."""
    manager.siemplify = MagicMock()
    incidents_data = [
        {
            "id": "1",
            "lastUpdateDateTime": "2023-01-01T00:00:00Z",
            "assignedTo": "user1@example.com",
            "tags": ["TagA", "TagB"],
        },
        {
            "id": "2",
            "lastUpdateDateTime": "2023-01-01T01:00:00Z",
            "assignedTo": "user2@example.com",
            "tags": ["TagC"],
        },
    ]

    with patch.object(
        manager, "_paginate_results", return_value=incidents_data
    ), patch.object(
        manager, "get_incident_alerts", return_value=[MagicMock()]
    ):
        incidents = manager.get_incidents(
            existing_incidents={},
            limit=10,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            statuses=["active"],
            detection_source=[],
            service_source=[],
            connector_starting_time=unix_now(),
            python_process_timeout=100,
            assignees=["user1@example.com"],
            tags=["TagA"],
        )

        assert len(incidents) == 1
        assert incidents[0].incident_id == "1"


def test_get_incidents_tags_filtering_with_dicts_and_nulls(manager):
    """Test get_incidents tag filtering with dict tags, None values, and numbers."""
    manager.siemplify = MagicMock()
    incidents_data = [
        {
            "id": "1",
            "lastUpdateDateTime": "2023-01-01T00:00:00Z",
            "tags": [{"name": "DictTag"}, None, 123],
        },
        {
            "id": "2",
            "lastUpdateDateTime": "2023-01-01T01:00:00Z",
            "tags": [None, "OtherTag"],
        },
    ]

    with patch.object(
        manager, "_paginate_results", return_value=incidents_data
    ), patch.object(
        manager, "get_incident_alerts", return_value=[MagicMock()]
    ):
        incidents = manager.get_incidents(
            existing_incidents={},
            limit=10,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            statuses=["active"],
            detection_source=[],
            service_source=[],
            connector_starting_time=unix_now(),
            python_process_timeout=100,
            tags=["DictTag"],
        )

        assert len(incidents) == 1
        assert incidents[0].incident_id == "1"


def test_get_incident_alerts_no_start_time_filter(manager):
    """Test get_incident_alerts does not restrict query with start_time."""
    manager.siemplify = MagicMock()
    manager.use_graph_api_for_alerts = True

    incident_mock = MagicMock()
    incident_mock.incident_id = "9789"
    incident_mock.last_update_time = "2026-07-22T11:42:05Z"
    incident_mock.raw_data = {"alerts": []}

    with patch.object(
        manager, "_paginate_results", return_value=[]
    ) as mock_paginate, patch.object(
        manager,
        "_build_api_params",
        return_value={"$filter": "incidentId eq '9789'"},
    ) as mock_build_params:

        alerts = manager.get_incident_alerts(
            incident=incident_mock,
            incidents_start_time=None,
            existing_alerts=set(),
            detection_source=[],
            service_source=[],
            is_tracking_enabled=False,
        )

        mock_build_params.assert_called_once_with(
            additional_filters={
                "incidentId": "9789",
                "detectionSource": [],
                "serviceSource": [],
            },
            graph=True,
        )
        assert "start_time" not in mock_build_params.call_args.kwargs


def test_get_incidents_odata_nextlink_pagination(manager):
    """Test _paginate_results using @odata.nextLink."""
    page1 = {
        "value": [{"id": "1"}],
        "@odata.nextLink": (
            "https://graph.microsoft.com/v1.0/security/incidents?$skiptoken=page2"
        ),
    }
    page2 = {
        "value": [{"id": "2"}]
    }

    mock_resp1 = MagicMock()
    mock_resp1.status_code = 200
    mock_resp1.json.return_value = page1

    mock_resp2 = MagicMock()
    mock_resp2.status_code = 200
    mock_resp2.json.return_value = page2

    manager.session.request.side_effect = [mock_resp1, mock_resp2]

    results = manager._paginate_results(
        method="GET",
        url="https://graph.microsoft.com/v1.0/security/incidents",
        params={},
        limit_per_request=50
    )

    assert len(results) == 2
    assert results[0]["id"] == "1"
    assert results[1]["id"] == "2"


def test_parser_fallback_title_extraction():
    """Test fallback title extraction logic in Microsoft365DefenderParser."""
    parser = Microsoft365DefenderParser()

    raw1 = {"title": "Title From Key"}
    alert1 = parser.build_alert_with_evidence_object(raw1)
    assert alert1.title == "Title From Key"

    raw2 = {"alertTitle": "Title From AlertTitle"}
    alert2 = parser.build_alert_with_evidence_object(raw2)
    assert alert2.title == "Title From AlertTitle"

    raw3 = {"displayName": "Title From DisplayName"}
    alert3 = parser.build_alert_with_evidence_object(raw3)
    assert alert3.title == "Title From DisplayName"


def test_alert_with_evidence_500_limit():
    """Test that AlertWithEvidence caps evidence events at 500 max."""

    evidences = [
        {
            "createdDateTime": (
                f"2026-08-01T{i//3600:02d}:{(i%3600)//60:02d}:{i%60:02d}Z"
            ),
            "evidence_id": i,
            "additionalData": {"junk": "data"},
        }
        for i in range(600)
    ]

    alert = AlertWithEvidence(
        raw_data={"id": "alert_123", "title": "Test Alert"},
        alert_id="alert_123",
        incident_id="inc_456",
        title="Test Alert",
        severity="High",
        assignee="admin@example.com",
        first_activity="2026-08-01T00:00:00Z",
        last_activity="2026-08-01T00:00:00Z",
        description="Test Alert Description",
        evidences=evidences,
    )

    incident_event = {"event_type": "Incident", "incidentId": "inc_456"}
    events = alert.create_events(incident_event)

    assert len(events) == 502
    assert events[0]["event_type"] == "Incident"
    assert events[1]["event_type"] == "Alert"

    evidence_events = events[2:]
    assert len(evidence_events) == 500
    for ev in evidence_events:
        assert ev["event_type"] == "Evidence"
        assert "additionalData" not in ev

    assert int(evidence_events[0]["evidence_id"]) == 100
    assert int(evidence_events[-1]["evidence_id"]) == 599


def test_get_alerts_by_ids_handles_not_found(manager):
    """Test that get_alerts_by_ids skips alerts that return NotFoundItemException."""
    def mock_get_alert(alert_id):
        if alert_id == "404_alert":
            raise NotFoundItemException("Alert not found")
        mock_alert = MagicMock()
        mock_alert.alert_id = alert_id
        return mock_alert

    with patch.object(manager, "get_alert", side_effect=mock_get_alert):
        alert_ids = ["valid_alert_1", "404_alert", "valid_alert_2"]
        alerts = manager.get_alerts_by_ids(alert_ids)
        assert len(alerts) == 2
        assert [a.alert_id for a in alerts] == ["valid_alert_1", "valid_alert_2"]


def test_get_alerts_by_ids_raises_on_non_404_exception(manager):
    """Test that get_alerts_by_ids re-raises non-404 exceptions."""
    with patch.object(manager, "get_alert", side_effect=Exception("Network failure")):
        with pytest.raises(Exception, match="Network failure"):
            manager.get_alerts_by_ids(["alert_1"])


def test_build_alert_object():
    """Test that Microsoft365DefenderParser.build_alert_with_evidence_object creates Alert without error."""
    from microsoft365_defender.core.Microsoft365DefenderParser import Microsoft365DefenderParser

    parser = Microsoft365DefenderParser()
    raw_alert = {
        "id": "alert-957744",
        "incidentId": "957744",
        "title": "Test Defender Alert",
        "severity": "high",
        "firstActivity": "2026-08-13T09:00:00Z",
        "lastActivity": "2026-08-13T09:10:00Z",
        "description": "Sample alert description",
        "assignedTo": "user@example.com",
    }
    alert = parser.build_alert_with_evidence_object(raw_data=raw_alert)
    assert alert.alert_id == "alert-957744"
    assert alert.incident_id == "957744"
    assert alert.title == "Test Defender Alert"
    assert alert.assignee == "user@example.com"

def test_get_incidents_passes_pagination_limit_no_filters(manager):
    """Test that get_incidents calculates pagination limit as limit when no assignees/tags."""
    manager.siemplify = MagicMock()
    with patch.object(manager, "_paginate_results", return_value=[]) as mock_paginate:
        manager.get_incidents(
            existing_incidents={},
            limit=5,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            statuses=["Active"],
            detection_source=[],
            service_source=[],
            assignees=None,
            tags=None,
            connector_starting_time=1000,
            python_process_timeout=600,
        )

        assert mock_paginate.called
        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["limit"] == 5
        assert call_kwargs["connector_starting_time"] == 1000
        assert call_kwargs["python_process_timeout"] == 600


def test_get_incidents_passes_pagination_limit_with_filters(manager):
    """Test that get_incidents calculates pagination limit as
    max(limit * 5, INCIDENTS_LIMIT_PER_REQUEST) when assignees/tags exist.
    """
    manager.siemplify = MagicMock()
    with patch.object(manager, "_paginate_results", return_value=[]) as mock_paginate:
        manager.get_incidents(
            existing_incidents={},
            limit=5,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            statuses=["Active"],
            detection_source=[],
            service_source=[],
            assignees=["user@example.com"],
            tags=None,
            connector_starting_time=1000,
            python_process_timeout=600,
        )

        assert mock_paginate.called
        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["limit"] == max(5 * 5, INCIDENTS_LIMIT_PER_REQUEST)


def test_get_incident_alerts_passes_limit_to_paginate_results(manager):
    """Test that get_incident_alerts specifies limit=ALERTS_LIMIT_PER_REQUEST."""
    manager.siemplify = MagicMock()
    mock_incident = MagicMock()
    mock_incident.incident_id = "12345"

    with patch.object(manager, "_paginate_results", return_value=[]) as mock_paginate, \
         patch.object(manager, "get_filtered_alerts", return_value=[]):
        manager.get_incident_alerts(
            incident=mock_incident,
            incidents_start_time=datetime.now(timezone.utc),
            existing_alerts=set(),
            detection_source=[],
            service_source=[],
        )

        assert mock_paginate.called
        call_kwargs = mock_paginate.call_args[1]
        assert call_kwargs["limit"] == ALERTS_LIMIT_PER_REQUEST
        assert call_kwargs["limit_per_request"] == ALERTS_LIMIT_PER_REQUEST


def test_paginate_results_respects_limit_in_next_link(manager):
    """Test that _paginate_results stops next_link pagination when limit is reached."""
    page_1 = {"value": [{"id": "1"}, {"id": "2"}], "@odata.nextLink": "http://next/page2"}
    page_2 = {"value": [{"id": "3"}, {"id": "4"}], "@odata.nextLink": "http://next/page3"}

    mock_resp1 = MagicMock()
    mock_resp1.json.return_value = page_1
    mock_resp1.status_code = 200

    mock_resp2 = MagicMock()
    mock_resp2.json.return_value = page_2
    mock_resp2.status_code = 200

    with patch.object(manager.session, "request", side_effect=[mock_resp1, mock_resp2]) as mock_request:
        results = manager._paginate_results(
            method="GET",
            url="http://test/incidents",
            limit=2,
        )

        assert len(results) == 2
        assert mock_request.call_count == 1


def test_paginate_results_breaks_on_timeout_in_next_link(manager):
    """Test that _paginate_results stops next_link pagination when approaching timeout."""
    manager.siemplify = MagicMock()
    page_1 = {"value": [{"id": "1"}], "@odata.nextLink": "http://next/page2"}

    mock_resp1 = MagicMock()
    mock_resp1.json.return_value = page_1
    mock_resp1.status_code = 200

    with patch.object(manager.session, "request", return_value=mock_resp1), \
         patch("Microsoft365DefenderManager.is_approaching_timeout", return_value=True):
        results = manager._paginate_results(
            method="GET",
            url="http://test/incidents",
            connector_starting_time=1000,
            python_process_timeout=600,
        )

        assert len(results) == 1


def test_paginate_results_breaks_on_timeout_in_skip_loop(manager):
    """Test that _paginate_results stops $skip pagination when approaching timeout."""
    manager.siemplify = MagicMock()
    page_1 = {"value": [{"id": "1"}] * INCIDENTS_LIMIT_PER_REQUEST}

    mock_resp1 = MagicMock()
    mock_resp1.json.return_value = page_1
    mock_resp1.status_code = 200

    with patch.object(manager.session, "request", return_value=mock_resp1), \
         patch("Microsoft365DefenderManager.is_approaching_timeout", side_effect=[False, True]):
        results = manager._paginate_results(
            method="GET",
            url="http://test/incidents",
            connector_starting_time=1000,
            python_process_timeout=600,
        )

        assert len(results) == INCIDENTS_LIMIT_PER_REQUEST


def test_add_comment_to_alert_skips_empty_comment(manager):
    """Test that add_comment_to_alert returns early and skips HTTP request
    for empty, None, or whitespace comment.
    """
    manager.add_comment_to_alert(alert_id="alert123", comment="")
    manager.session.post.assert_not_called()

    manager.add_comment_to_alert(alert_id="alert123", comment=None)
    manager.session.post.assert_not_called()

    manager.add_comment_to_alert(alert_id="alert123", comment="   ")
    manager.session.post.assert_not_called()
