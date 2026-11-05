from __future__ import annotations

import json

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Entity ID": "68599", "Entity Type": "Host"}


class TestDescribeEntity:
    def test_describe_entity_success(self, siemplify, mock_session, product):
        action = load_action("Describe Entity")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved information for entity ID 68599" in output.output_message
        returned = json.loads(siemplify.result.json_output)
        assert returned["id"] == 68599

    def test_describe_entity_not_found(self, siemplify, mock_session, product):
        product.describe_entity_response = []
        action = load_action("Describe Entity")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Entity not found" in output.output_message

    def test_describe_entity_invalid_id(self, siemplify, mock_session, product):
        action = load_action("Describe Entity")
        output = run_action(action, siemplify, {"Entity ID": "abc", "Entity Type": "Host"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
