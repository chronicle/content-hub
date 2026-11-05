from __future__ import annotations

import json

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action


class TestListAssignments:
    def test_list_assignments_success(self, siemplify, mock_session, product):
        action = load_action("List Assignments")
        output = run_action(action, siemplify, {})

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved 1 assignments." in output.output_message
        returned = json.loads(siemplify.result.json_output)
        assert returned[0]["id"] == 63

    def test_list_assignments_no_results(self, siemplify, mock_session, product):
        product.list_assignments_response = []
        action = load_action("List Assignments")
        output = run_action(action, siemplify, {})

        assert output.result_value is True
        assert output.output_message == "No assignments found with provided parameters"

    def test_list_assignments_invalid_limit(self, siemplify, mock_session, product):
        action = load_action("List Assignments")
        output = run_action(action, siemplify, {"Limit": "0"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_list_assignments_invalid_account_ids(self, siemplify, mock_session, product):
        action = load_action("List Assignments")
        output = run_action(action, siemplify, {"Accounts IDs": "not-a-number"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
