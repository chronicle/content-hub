from __future__ import annotations

from typing import Any

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession

DEFAULT_PARAMETERS = {"User ID": "101", "Entity ID": "68599", "Entity Type": "Host"}


class TestAssignEntity:
    def test_assign_entity_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Assign Entity")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Assignment created successfully with ID: 64" in output.output_message

    def test_assign_entity_invalid_entity_id(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Assign Entity")
        params = dict(DEFAULT_PARAMETERS)
        params["Entity ID"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_assign_entity_api_error(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.fail("ASSIGN_ENTITY", 404, {"detail": "Not found."})
        action = load_action("Assign Entity")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
