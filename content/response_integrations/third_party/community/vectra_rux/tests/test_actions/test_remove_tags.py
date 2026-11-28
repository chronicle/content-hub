from __future__ import annotations

from typing import Any

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession

DEFAULT_PARAMETERS = {"Tags": "test-tag", "Entity ID": "103", "Entity Type": "Account"}


class TestRemoveTags:
    def test_remove_tags_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Remove Tags")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert 'Successfully removed tag(s): "test-tag"' in output.output_message

    def test_remove_tags_not_present(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.list_tags_response = {"status": "success", "tags": ["other-tag"]}
        action = load_action("Remove Tags")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "don't exist" in output.output_message

    def test_remove_tags_invalid_entity_id(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("Remove Tags")
        params = dict(DEFAULT_PARAMETERS)
        params["Entity ID"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_remove_tags_entity_not_found(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.fail("LIST_TAGS", 404, {"message": "not found", "status": "failed"})
        action = load_action("Remove Tags")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
