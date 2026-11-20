from __future__ import annotations

from typing import Any

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession

DEFAULT_PARAMETERS = {"Entity ID": "68599", "Entity Type": "Host"}


class TestListTags:
    def test_list_tags_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("List Tags")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Fetch List of Tags" in output.output_message

    def test_list_tags_failed_status(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.list_tags_response = {"status": "failed", "tags": []}
        action = load_action("List Tags")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert output.output_message == "Failed to Fetch the Tags"

    def test_list_tags_invalid_entity_id(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("List Tags")
        output = run_action(action, siemplify, {"Entity ID": "abc", "Entity Type": "Host"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_list_tags_entity_not_found(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.fail("LIST_TAGS", 404, {"message": "not found", "status": "failed"})
        action = load_action("List Tags")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Entity not found" in output.output_message
