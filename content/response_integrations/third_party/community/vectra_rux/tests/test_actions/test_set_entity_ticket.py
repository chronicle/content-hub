from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Entity ID": "101", "Entity Type": "Account", "External Reference ID": "12345"}


class TestSetEntityTicket:
    def test_set_entity_ticket_success(self, siemplify, mock_session, product):
        action = load_action("Set Entity Ticket")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "updated as 12345" in output.output_message

    def test_set_entity_ticket_invalid_entity_id(self, siemplify, mock_session, product):
        action = load_action("Set Entity Ticket")
        params = dict(DEFAULT_PARAMETERS)
        params["Entity ID"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_set_entity_ticket_not_found(self, siemplify, mock_session, product):
        product.fail("SET_ENTITY_TICKET", 404, {"detail": "Not found."})
        action = load_action("Set Entity Ticket")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Entity not found" in output.output_message
