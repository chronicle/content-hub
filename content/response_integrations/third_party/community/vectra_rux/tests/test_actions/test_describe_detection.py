from __future__ import annotations

import json

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Detection ID": "34338"}


class TestDescribeDetection:
    def test_describe_detection_success(self, siemplify, mock_session, product):
        action = load_action("Describe Detection")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved information for detection ID 34338" in output.output_message
        returned = json.loads(siemplify.result.json_output)
        assert returned["id"] == 34338

    def test_describe_detection_not_found(self, siemplify, mock_session, product):
        product.describe_detection_response = []
        action = load_action("Describe Detection")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Detection not found" in output.output_message

    def test_describe_detection_invalid_id(self, siemplify, mock_session, product):
        action = load_action("Describe Detection")
        output = run_action(action, siemplify, {"Detection ID": "abc"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
