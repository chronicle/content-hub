from __future__ import annotations

import json

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Assignment ID": "63"}


class TestDescribeAssignment:
    def test_describe_assignment_success(self, siemplify, mock_session, product):
        action = load_action("Describe Assignment")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved information for assignment ID 63" in output.output_message
        returned = json.loads(siemplify.result.json_output)
        assert returned["assignment"]["id"] == 63

    def test_describe_assignment_not_found(self, siemplify, mock_session, product):
        product.fail("ASSIGNMENT", 404, {"detail": "Not found."})
        action = load_action("Describe Assignment")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Assignment not found" in output.output_message

    def test_describe_assignment_invalid_id(self, siemplify, mock_session, product):
        action = load_action("Describe Assignment")
        output = run_action(action, siemplify, {"Assignment ID": "abc"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
