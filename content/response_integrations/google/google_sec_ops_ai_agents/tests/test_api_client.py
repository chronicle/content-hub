from __future__ import annotations

from unittest.mock import patch

import pytest
from google_sec_ops_ai_agents.core.api_client import (
    ChronicleInvestigationApiClient,
)
from google_sec_ops_ai_agents.core.exceptions import (
    ChronicleInvestigationManagerError,
)


def test_test_connectivity_success(api_client: ChronicleInvestigationApiClient):
    """Test for successful connectivity."""
    with patch.object(api_client, "list_investigations") as mock_list_investigations:
        mock_list_investigations.return_value = {}
        assert api_client.test_connectivity() is None
        mock_list_investigations.assert_called_once_with(
            alert_id="siemplify-connectivity-test",
            page_size=1,
        )


def test_test_connectivity_failure(api_client: ChronicleInvestigationApiClient):
    """Test for failed connectivity."""
    with patch.object(api_client, "list_investigations") as mock_list_investigations:
        mock_list_investigations.side_effect = ChronicleInvestigationManagerError("Failed")
        with pytest.raises(ChronicleInvestigationManagerError):
            api_client.test_connectivity()


def test_trigger_investigation(api_client: ChronicleInvestigationApiClient):
    """Test triggering an investigation."""
    alert_id = "test_alert"
    expected_response = {"status": "triggered"}
    api_client.session.post.return_value.json.return_value = expected_response
    api_client.session.post.return_value.status_code = 200

    response = api_client.trigger_investigation(alert_id)

    assert response == expected_response
    api_client.session.post.assert_called_once()


def test_get_investigation_status(api_client: ChronicleInvestigationApiClient):
    """Test getting investigation status."""
    investigation_name = "test_investigation"
    expected_response = {"status": "complete"}
    api_client.session.get.return_value.json.return_value = expected_response
    api_client.session.get.return_value.status_code = 200

    response = api_client.get_investigation_status(investigation_name)

    assert response == expected_response
    api_client.session.get.assert_called_once()


def test_list_investigations(api_client: ChronicleInvestigationApiClient):
    """Test listing investigations."""
    alert_id = "test_alert"
    expected_response = {"investigations": []}
    api_client.session.get.return_value.json.return_value = expected_response
    api_client.session.get.return_value.status_code = 200

    response = api_client.list_investigations(alert_id)

    assert response == []
    api_client.session.get.assert_called_once()
