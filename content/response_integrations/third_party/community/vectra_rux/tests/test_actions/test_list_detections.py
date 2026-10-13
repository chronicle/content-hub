from __future__ import annotations

import json

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {}


class TestListDetections:
    def test_list_detections_success(self, siemplify, mock_session, product):
        action = load_action("List Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved the details for 1 detections" in output.output_message
        returned = json.loads(siemplify.result.json_output)
        assert returned[0]["id"] == 34338

    def test_list_detections_no_results(self, siemplify, mock_session, product):
        product.list_detections_response = []
        action = load_action("List Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.output_message == "No detections were found for the provided parameters"

    def test_list_detections_invalid_threat_gte(self, siemplify, mock_session, product):
        action = load_action("List Detections")
        output = run_action(action, siemplify, {"Threat GTE": "not-a-number"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
