from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Group ID": "73", "Members": "test.domain.com"}


class TestAssignGroup:
    def test_assign_group_success(self, siemplify, mock_session, product):
        action = load_action("Assign Group")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully assigned 1 members" in output.output_message
        assert len(siemplify.result.html_reports) == 1

    def test_assign_group_no_members_assigned(self, siemplify, mock_session, product):
        product.group_update_response = {
            "id": 73,
            "name": "New Group test domain",
            "type": "domain",
            "members": [],
        }
        action = load_action("Assign Group")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "No members were assigned" in output.output_message

    def test_assign_group_invalid_group_id(self, siemplify, mock_session, product):
        action = load_action("Assign Group")
        params = dict(DEFAULT_PARAMETERS)
        params["Group ID"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_assign_group_not_found(self, siemplify, mock_session, product):
        product.fail("UPDATE_GROUP_MEMBERS", 404, {"detail": "not found"})
        action = load_action("Assign Group")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
