from __future__ import annotations

import json

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action


class TestListGroups:
    def test_list_groups_success(self, siemplify, mock_session, product):
        action = load_action("List Groups")
        output = run_action(action, siemplify, {})

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved 1 groups." in output.output_message
        returned = json.loads(siemplify.result.json_output)
        assert returned[0]["id"] == 73

    def test_list_groups_no_results(self, siemplify, mock_session, product):
        product.list_groups_response = []
        action = load_action("List Groups")
        output = run_action(action, siemplify, {})

        assert output.result_value is True
        assert output.output_message == "No groups were found with the provided parameters."

    def test_list_groups_invalid_limit(self, siemplify, mock_session, product):
        action = load_action("List Groups")
        output = run_action(action, siemplify, {"Limit": "0"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_list_groups_uri_too_long(self, siemplify, mock_session, product):
        product.fail("LIST_GROUPS", 414)
        action = load_action("List Groups")
        output = run_action(action, siemplify, {"Host Names": "a" * 5000})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
