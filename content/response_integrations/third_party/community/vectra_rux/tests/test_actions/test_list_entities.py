from __future__ import annotations

import json

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {
    "Entity Type": "Host",
    "Fields": "[]",
}


class TestListEntities:
    def test_list_entities_success(self, siemplify, mock_session, product):
        action = load_action("List Entities")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved the details for 1 entities" in output.output_message
        assert len(siemplify.result.data_tables) == 1
        assert siemplify.result.data_tables[0]["title"] == "List Of Entities"

        returned = json.loads(siemplify.result.json_output)
        assert returned[0]["id"] == 64512

    def test_list_entities_no_results(self, siemplify, mock_session, product):
        product.list_entities_response = []
        action = load_action("List Entities")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.output_message == "No entities were found for the given parameters"
        assert siemplify.result.data_tables == []

    def test_list_entities_invalid_limit(self, siemplify, mock_session, product):
        action = load_action("List Entities")
        params = dict(DEFAULT_PARAMETERS)
        params["Limit"] = "0"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Limit" in output.output_message

    def test_list_entities_api_error(self, siemplify, mock_session, product):
        product.fail("LIST_ENTITIES", 400, {"detail": "bad filter"})
        action = load_action("List Entities")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
