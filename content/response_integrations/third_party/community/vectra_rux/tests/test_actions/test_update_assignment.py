from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Entity ID": "68599", "Entity Type": "Host", "User ID": "101"}


class TestUpdateAssignment:
    def test_update_assignment_success(self, siemplify, mock_session, product):
        action = load_action("Update Assignment")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully updated assignment-63 to user ID-101" in output.output_message

    def test_update_assignment_entity_has_no_assignment(self, siemplify, mock_session, product):
        product.specific_entity_info_response = {"id": 68599, "type": "host", "assignment": None}
        action = load_action("Update Assignment")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "doesn't have assignment" in output.output_message

    def test_update_assignment_invalid_user_id(self, siemplify, mock_session, product):
        action = load_action("Update Assignment")
        params = dict(DEFAULT_PARAMETERS)
        params["User ID"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_update_assignment_not_permitted(self, siemplify, mock_session, product):
        product.fail(
            "UPDATE_ASSIGNMENT",
            400,
            {"errors": [{"title": "User not permitted to resolve this assignment"}]},
        )
        action = load_action("Update Assignment")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
