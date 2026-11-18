from __future__ import annotations

from typing import Any

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession

DEFAULT_PARAMETERS = {"Query": "hosts()"}


class TestQueryInvestigation:
    def test_query_investigation_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Query Investigation")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "req-123456" in output.output_message

    def test_query_investigation_with_version(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Query Investigation")
        params = dict(DEFAULT_PARAMETERS)
        params["Version"] = "2"
        output = run_action(action, siemplify, params)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED

    def test_query_investigation_api_error(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.fail("QUERY_INVESTIGATION", 400, {"detail": "invalid query"})
        action = load_action("Query Investigation")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "failed to start" in output.output_message
