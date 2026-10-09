from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Entity ID": "68599", "Entity Type": "Host"}


class TestRemoveAssignment:
    def test_remove_assignment_success(self, siemplify, mock_session, product):
        action = load_action("Remove Assignment")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully deleted assignment with entity ID 68599" in output.output_message

    def test_remove_assignment_no_assignment(self, siemplify, mock_session, product):
        product.specific_entity_info_response = {"id": 68599, "type": "host", "assignment": None}
        action = load_action("Remove Assignment")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "doesn't have assignment" in output.output_message

    def test_remove_assignment_invalid_entity_id(self, siemplify, mock_session, product):
        action = load_action("Remove Assignment")
        output = run_action(action, siemplify, {"Entity ID": "abc", "Entity Type": "Host"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_remove_assignment_delete_returns_non_empty_body(self, siemplify, mock_session, product):
        product.remove_assignment_body = b'{"error": "still pending"}'
        action = load_action("Remove Assignment")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Failed to delete assignment" in output.output_message

    def test_remove_assignment_delete_not_found(self, siemplify, mock_session, product):
        product.remove_assignment_status_code = 404
        action = load_action("Remove Assignment")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
