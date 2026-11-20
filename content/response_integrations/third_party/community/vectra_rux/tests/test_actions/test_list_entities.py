from __future__ import annotations

from typing import Any

import json

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action
from tests.core.product import VectraProduct
from tests.core.session import MockVectraSession

DEFAULT_PARAMETERS = {
    "Entity Type": "Host",
    "Fields": "[]",
}


class TestListEntities:
    def test_list_entities_success(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("List Entities")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved the details for 1 entities" in output.output_message
        assert len(siemplify.result.data_tables) == 1
        assert siemplify.result.data_tables[0]["title"] == "List Of Entities"

        returned = json.loads(siemplify.result.json_output)
        assert returned[0]["id"] == 64512

    def test_list_entities_no_results(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.list_entities_response = []
        action = load_action("List Entities")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.output_message == "No entities were found for the given parameters"
        assert siemplify.result.data_tables == []

    def test_list_entities_invalid_limit(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        action = load_action("List Entities")
        params = dict(DEFAULT_PARAMETERS)
        params["Limit"] = "0"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Limit" in output.output_message

    def test_list_entities_api_error(
        self,
        siemplify: Any,
        mock_session: MockVectraSession,
        product: VectraProduct,
    ) -> None:
        product.fail("LIST_ENTITIES", 400, {"detail": "bad filter"})
        action = load_action("List Entities")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
