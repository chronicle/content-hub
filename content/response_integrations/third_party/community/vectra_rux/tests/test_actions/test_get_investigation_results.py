from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Request ID": "req-123456"}


class TestGetInvestigationResults:
    def test_get_investigation_results_success(self, siemplify, mock_session, product):
        action = load_action("Get Investigation Results")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Retrieved 1 investigation results for req-123456" in output.output_message

    def test_get_investigation_results_no_results(self, siemplify, mock_session, product):
        product.investigation_results_response = []
        action = load_action("Get Investigation Results")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert "No investigation results were found" in output.output_message

    def test_get_investigation_results_invalid_limit(self, siemplify, mock_session, product):
        action = load_action("Get Investigation Results")
        params = dict(DEFAULT_PARAMETERS)
        params["Limit"] = "0"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_get_investigation_results_not_found(self, siemplify, mock_session, product):
        product.fail("GET_INVESTIGATION_RESULTS", 404, {"detail": "Not found."})
        action = load_action("Get Investigation Results")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
