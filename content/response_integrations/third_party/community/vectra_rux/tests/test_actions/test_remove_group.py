from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Group ID": "73", "Members": "test.domain.com"}


class TestRemoveGroup:
    def test_remove_group_success(self, siemplify, mock_session, product):
        action = load_action("Remove Group")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully removed 1 members" in output.output_message
        assert len(siemplify.result.html_reports) == 1

    def test_remove_group_no_members_removed(self, siemplify, mock_session, product):
        product.group_members_response = {"type": "domain", "members": ["other.domain.com"]}
        action = load_action("Remove Group")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "No members were removed" in output.output_message

    def test_remove_group_invalid_group_id(self, siemplify, mock_session, product):
        action = load_action("Remove Group")
        params = dict(DEFAULT_PARAMETERS)
        params["Group ID"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_remove_group_not_found(self, siemplify, mock_session, product):
        product.fail("UPDATE_GROUP_MEMBERS", 404, {"detail": "not found"})
        action = load_action("Remove Group")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
