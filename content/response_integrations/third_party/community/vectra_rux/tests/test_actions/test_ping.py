from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action


class TestPing:
    def test_ping_success(self, siemplify, mock_session, product):
        from tests.conftest import run_action

        action = load_action("Ping")
        output = run_action(action, siemplify, {})

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert output.output_message == "Successfully connected to the VectraRUX server"
        assert len(mock_session.request_history) >= 1
        assert mock_session.request_history[0]["url"].endswith("oauth2/token")

    def test_ping_failure_invalid_credentials(self, siemplify, mock_session, product):
        from tests.conftest import run_action

        product.token_status_code = 401
        action = load_action("Ping")
        output = run_action(action, siemplify, {})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Failed to connect to the Vectra server" in output.output_message
