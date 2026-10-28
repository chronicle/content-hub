from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Detection IDs": "101, 102", "Reason": "Remediated"}


class TestCloseDetections:
    def test_close_detections_success(self, siemplify, mock_session, product):
        action = load_action("Close Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "successfully closed as remediated" in output.output_message

    def test_close_detections_invalid_ids(self, siemplify, mock_session, product):
        action = load_action("Close Detections")
        params = dict(DEFAULT_PARAMETERS)
        params["Detection IDs"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_close_detections_not_found(self, siemplify, mock_session, product):
        product.fail("CLOSE_DETECTIONS", 404, {"detail": "Not found."})
        action = load_action("Close Detections")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Invalid Detection IDs" in output.output_message
