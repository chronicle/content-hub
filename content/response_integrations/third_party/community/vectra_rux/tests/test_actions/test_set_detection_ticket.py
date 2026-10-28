from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Detection IDs": "101,102", "External Reference ID": "12345"}


class TestSetDetectionTicket:
    def test_set_detection_ticket_success(self, siemplify, mock_session, product):
        action = load_action("Set Detection Ticket")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "updated as 12345" in output.output_message

    def test_set_detection_ticket_invalid_detection_ids(self, siemplify, mock_session, product):
        action = load_action("Set Detection Ticket")
        params = dict(DEFAULT_PARAMETERS)
        params["Detection IDs"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_set_detection_ticket_api_error(self, siemplify, mock_session, product):
        product.fail("SET_DETECTION_TICKET", 400, {"detail": "invalid ids"})
        action = load_action("Set Detection Ticket")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
