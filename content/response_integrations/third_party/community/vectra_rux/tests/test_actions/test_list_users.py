from __future__ import annotations

from typing import Any

import json

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession


class TestListUsers:
    def test_list_users_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("List Users")
        output = run_action(action, siemplify, {})

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved the 1 users" in output.output_message
        returned = json.loads(siemplify.result.json_output)
        assert returned[0]["email"] == "test.user@example.com"

    def test_list_users_no_results(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.list_users_response = []
        action = load_action("List Users")
        output = run_action(action, siemplify, {})

        assert output.result_value is True
        assert output.output_message == "No users were found with the provided parameters."

    def test_list_users_invalid_limit(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("List Users")
        output = run_action(action, siemplify, {"Limit": "0"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_list_users_api_error(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.fail("LIST_USERS", 400, {"detail": "bad role"})
        action = load_action("List Users")
        output = run_action(action, siemplify, {"Role": "InvalidRole"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
