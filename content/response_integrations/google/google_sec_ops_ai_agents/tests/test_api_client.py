from __future__ import annotations

from unittest.mock import patch

import pytest
from google_sec_ops_ai_agents.core.data_models import (
    RemediationActionExecution,
    RemediationActionExecutionsList,
    RemediationPlan,
    RemediationPlanList,
)
from google_sec_ops_ai_agents.core.api_client import ChronicleInvestigationApiClient
from google_sec_ops_ai_agents.core.exceptions import ChronicleInvestigationManagerError


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


def test_list_remediation_plans(api_client: ChronicleInvestigationApiClient):
    """Test listing remediation plans on a single page."""
    alert_id = "test_alert"
    expected_response = {"remediationPlans": [{"name": "plan-1"}]}
    api_client.session.get.return_value.json.return_value = expected_response
    api_client.session.get.return_value.status_code = 200

    response = api_client.list_remediation_plans(alert_id)

    assert response == [{"name": "plan-1"}]
    api_client.session.get.assert_called_once_with(
        f"{api_client.api_params.api_root}/remediationPlans",
        params={"filter": '(siemAlertId="test_alert")'},
    )


def test_list_remediation_plans_pagination(api_client: ChronicleInvestigationApiClient):
    """Test listing remediation plans across multiple pages with page_token."""
    alert_id = "test_alert"
    page1 = {
        "remediationPlans": [{"name": "plan-1"}, {"name": "plan-2"}],
        "nextPageToken": "token-page-2",
    }
    page2 = {
        "remediationPlans": [{"name": "plan-3"}],
        "nextPageToken": "",
    }

    mock_resp1 = patch("requests.Response").start()
    mock_resp1.json.return_value = page1
    mock_resp1.status_code = 200

    mock_resp2 = patch("requests.Response").start()
    mock_resp2.json.return_value = page2
    mock_resp2.status_code = 200

    api_client.session.get.side_effect = [mock_resp1, mock_resp2]

    response = api_client.list_remediation_plans(alert_id, page_size=2)

    assert len(response) == 3
    assert response == [{"name": "plan-1"}, {"name": "plan-2"}, {"name": "plan-3"}]
    assert api_client.session.get.call_count == 2
    # Verify second call included page_token
    second_call_params = api_client.session.get.call_args_list[1].kwargs["params"]
    assert second_call_params["pageToken"] == "token-page-2"
    assert second_call_params["pageSize"] == 2


def test_list_remediation_plans_with_options(api_client: ChronicleInvestigationApiClient):
    """Test listing remediation plans with expand, order_by, and limit."""
    expected_response = {
        "remediationPlans": [{"name": "plan-1"}, {"name": "plan-2"}]
    }
    api_client.session.get.return_value.json.return_value = expected_response
    api_client.session.get.return_value.status_code = 200

    response = api_client.list_remediation_plans(
        filter="state = 'SUGGESTED'",
        order_by="create_time desc",
        expand="actions, latest_execution",
        limit=1,
    )

    assert len(response) == 1
    assert response == [{"name": "plan-1"}]
    call_params = api_client.session.get.call_args.kwargs["params"]
    assert call_params["filter"] == "state = 'SUGGESTED'"
    assert call_params["orderBy"] == "create_time desc"
    assert call_params["expand"] == "actions, latest_execution"


def test_paginate_returns_raw_dicts(api_client: ChronicleInvestigationApiClient):
    """Test generic paginate method returning raw dictionaries."""
    mock_response = {
        "remediationPlans": [{"name": "plan-1"}, {"name": "plan-2"}],
        "nextPageToken": None,
    }
    api_client.session.get.return_value.json.return_value = mock_response
    api_client.session.get.return_value.status_code = 200

    response = api_client.paginate(
        url="https://test.com/items",
        results_key="remediationPlans",
    )

    assert len(response) == 2
    assert response == [{"name": "plan-1"}, {"name": "plan-2"}]


def test_paginate_stops_when_total_size_reached(api_client: ChronicleInvestigationApiClient):
    """Test that pagination safely stops when collected items count reaches total_size."""
    mock_page = {
        "remediationPlans": [{"name": "plan-1"}],
        "nextPageToken": "still-has-token",
        "totalSize": 1,
    }
    api_client.session.get.return_value.json.return_value = mock_page
    api_client.session.get.return_value.status_code = 200

    response = api_client.paginate(
        url="https://test.com/items",
        results_key="remediationPlans",
    )

    assert len(response) == 1
    assert response == [{"name": "plan-1"}]
    assert api_client.session.get.call_count == 1


def test_generate_remediation_plan(
    api_client: ChronicleInvestigationApiClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """Test generating a remediation plan with default derived parent from environment."""
    monkeypatch.setenv("ONE_PLATFORM_URL_PROJECT", "test-project")
    monkeypatch.setenv("ONE_PLATFORM_URL_LOCATION", "us")
    monkeypatch.setenv("ONE_PLATFORM_URL_INSTANCE", "test-instance")

    alert_id = "test_alert"
    expected_response = {
        "name": "projects/p/locations/l/instances/i/remediationPlans/123"
    }
    api_client.session.post.return_value.json.return_value = expected_response
    api_client.session.post.return_value.status_code = 200

    response = api_client.generate_remediation_plan(alert_id)

    assert response == expected_response
    api_client.session.post.assert_called_once()
    call_args = api_client.session.post.call_args
    assert call_args.kwargs["json"] == {
        "parent": "projects/test-project/locations/us/instances/test-instance",
        "siemAlertId": "test_alert",
    }


def test_get_remediation_plan(api_client: ChronicleInvestigationApiClient):
    """Test getting a remediation plan."""
    plan_id = 123
    expected_response = {
        "name": "projects/p/locations/l/instances/i/remediationPlans/123"
    }
    api_client.session.get.return_value.json.return_value = expected_response
    api_client.session.get.return_value.status_code = 200

    response = api_client.get_remediation_plan(plan_id)

    assert response == expected_response
    api_client.session.get.assert_called_once()


def test_list_remediation_action_executions(
    api_client: ChronicleInvestigationApiClient,
):
    """Test listing remediation action executions."""
    plan_id = 123
    expected_response = {
        "remediationActionExecutions": [{"name": "exec-1"}],
    }
    api_client.session.get.return_value.json.return_value = expected_response
    api_client.session.get.return_value.status_code = 200

    response = api_client.list_remediation_action_executions(plan_id)

    assert response == [{"name": "exec-1"}]
    api_client.session.get.assert_called_once_with(
        f"{api_client.api_params.api_root}/remediationPlans/{plan_id}/"
        "remediationActions/-/remediationActionExecutions",
        params={},
    )


def test_list_remediation_action_executions_pagination(
    api_client: ChronicleInvestigationApiClient,
):
    """Test listing remediation action executions across multiple pages with page_token."""
    plan_id = 123
    page1 = {
        "remediationActionExecutions": [{"name": "exec-1"}, {"name": "exec-2"}],
        "nextPageToken": "token-page-2",
    }
    page2 = {
        "remediationActionExecutions": [{"name": "exec-3"}],
        "nextPageToken": "",
    }

    mock_resp1 = patch("requests.Response").start()
    mock_resp1.json.return_value = page1
    mock_resp1.status_code = 200

    mock_resp2 = patch("requests.Response").start()
    mock_resp2.json.return_value = page2
    mock_resp2.status_code = 200

    api_client.session.get.side_effect = [mock_resp1, mock_resp2]

    response = api_client.list_remediation_action_executions(plan_id, page_size=2)

    assert len(response) == 3
    assert response == [{"name": "exec-1"}, {"name": "exec-2"}, {"name": "exec-3"}]
    assert api_client.session.get.call_count == 2
    second_call_params = api_client.session.get.call_args_list[1].kwargs["params"]
    assert second_call_params["pageToken"] == "token-page-2"
    assert second_call_params["pageSize"] == 2


def test_list_remediation_action_executions_with_options(
    api_client: ChronicleInvestigationApiClient,
):
    """Test listing remediation action executions with filter, order_by, and include_all_executions."""
    plan_id = 123
    expected_response = {
        "remediationActionExecutions": [{"name": "exec-1"}, {"name": "exec-2"}]
    }
    api_client.session.get.return_value.json.return_value = expected_response
    api_client.session.get.return_value.status_code = 200

    response = api_client.list_remediation_action_executions(
        plan_id=plan_id,
        filter="state = 'SUCCESS'",
        order_by="create_time desc",
        include_all_executions=True,
        limit=1,
    )

    assert len(response) == 1
    assert response == [{"name": "exec-1"}]
    call_params = api_client.session.get.call_args.kwargs["params"]
    assert call_params["filter"] == "state = 'SUCCESS'"
    assert call_params["orderBy"] == "create_time desc"
    assert call_params["includeAllExecutions"] is True


def test_manager_list_remediation_plans(api_client: ChronicleInvestigationApiClient):
    """Test RemediationManager deserializing raw dicts into RemediationPlanList."""
    from unittest.mock import MagicMock
    from google_sec_ops_ai_agents.core.remediation_manager import RemediationManager

    logger = MagicMock()
    mgr = RemediationManager(api_client, logger)
    api_client.session.get.return_value.json.return_value = {
        "remediationPlans": [{"name": "plan-1"}]
    }
    api_client.session.get.return_value.status_code = 200

    result = mgr.list_remediation_plans("alert-1")
    assert isinstance(result, RemediationPlanList)
    assert len(result.remediation_plans) == 1
    assert isinstance(result.remediation_plans[0], RemediationPlan)
    assert result.remediation_plans[0].name == "plan-1"


def test_manager_list_remediation_action_executions(api_client: ChronicleInvestigationApiClient):
    """Test RemediationManager deserializing raw dicts into RemediationActionExecutionsList."""
    from unittest.mock import MagicMock
    from google_sec_ops_ai_agents.core.remediation_manager import RemediationManager

    logger = MagicMock()
    mgr = RemediationManager(api_client, logger)
    api_client.session.get.return_value.json.return_value = {
        "remediationActionExecutions": [{"name": "exec-1"}]
    }
    api_client.session.get.return_value.status_code = 200

    result = mgr.list_remediation_action_executions(123)
    assert isinstance(result, RemediationActionExecutionsList)
    assert len(result.remediation_action_executions) == 1
    assert isinstance(result.remediation_action_executions[0], RemediationActionExecution)
    assert result.remediation_action_executions[0].name == "exec-1"

