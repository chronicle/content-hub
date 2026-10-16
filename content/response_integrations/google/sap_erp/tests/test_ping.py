import pytest
import requests
from TIPCommon.base.action import ExecutionState

from sap_erp.actions.ping import FAILURE_PREFIX, SUCCESS_MESSAGE, PingAction
from sap_erp.core.sap_erp_manager import SapErpAuthError


def build_action(manager):
    action = PingAction(name="Ping")
    action._api_client = manager
    action.cloud_run_url = "https://gw-abc.a.run.app"
    return action


def assert_failed(action, message_substring):
    assert action.result_value is False
    assert action.execution_state == ExecutionState.FAILED
    # mp validate requires the standard Ping failure wording.
    assert action.output_message.startswith(FAILURE_PREFIX)
    assert FAILURE_PREFIX.startswith("Failed to connect to the")
    assert message_substring in action.output_message


# The gateway only accepts POST, so a healthy service answers GET with 405.
@pytest.mark.parametrize("status_code", [200, 405])
def test_healthy(manager, make_response, status_code):
    manager.ping.return_value = make_response(
        status_code, {"error": "Only POST requests are supported."}
    )
    action = build_action(manager)

    action._perform_action()

    assert action.result_value is True
    assert action.execution_state == ExecutionState.COMPLETED
    assert action.output_message == SUCCESS_MESSAGE
    assert SUCCESS_MESSAGE.startswith("Successfully connected to the")


@pytest.mark.parametrize("status_code", [401, 403])
def test_iam_rejected(manager, make_response, status_code):
    manager.ping.return_value = make_response(status_code, text="Forbidden")
    action = build_action(manager)

    action._perform_action()

    assert_failed(action, f"Authentication to Cloud Run failed (HTTP {status_code})")
    assert "roles/run.invoker" in action.output_message


def test_unexpected_status(manager, make_response):
    manager.ping.return_value = make_response(503, {"error": "Service Unavailable"})
    action = build_action(manager)

    action._perform_action()

    assert_failed(
        action, "Cloud Run service returned unexpected HTTP 503: Service Unavailable"
    )


def test_token_failure(manager):
    manager.ping.side_effect = SapErpAuthError("no creds")
    action = build_action(manager)

    action._perform_action()

    assert_failed(action, "Failed to generate Google Cloud authentication token.")


def test_network_error(manager):
    manager.ping.side_effect = requests.exceptions.ConnectionError("DNS failure")
    action = build_action(manager)

    action._perform_action()

    assert_failed(action, "Network error: DNS failure")
