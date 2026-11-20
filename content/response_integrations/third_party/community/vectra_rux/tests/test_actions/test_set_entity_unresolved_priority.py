from __future__ import annotations

from typing import Any

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession

DEFAULT_PARAMETERS = {"Entity ID": "101", "Entity Type": "Account"}


class TestSetEntityUnresolvedPriority:
    def test_set_entity_unresolved_priority_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Set Entity Unresolved Priority")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "successfully changed as false" in output.output_message

    def test_set_entity_unresolved_priority_invalid_entity_id(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Set Entity Unresolved Priority")
        output = run_action(action, siemplify, {"Entity ID": "abc", "Entity Type": "Account"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_set_entity_unresolved_priority_not_found(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.fail("SET_ENTITY_UNRESOLVED_PRIORITY", 404, {"detail": "Not found."})
        action = load_action("Set Entity Unresolved Priority")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Entity not found" in output.output_message
