from __future__ import annotations

import json

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Entity ID": "68599", "Entity Type": "Host"}


class TestListEntityNotes:
    def test_list_entity_notes_success(self, siemplify, mock_session, product):
        action = load_action("List Entity Notes")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert "Successfully retrieved 1 entity notes" in output.output_message
        returned = json.loads(siemplify.result.json_output)
        assert returned[0]["id"] == 9118

    def test_list_entity_notes_no_results(self, siemplify, mock_session, product):
        product.list_entity_notes_response = []
        action = load_action("List Entity Notes")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.output_message == "No notes were found for entity ID 68599"

    def test_list_entity_notes_invalid_entity_id(self, siemplify, mock_session, product):
        action = load_action("List Entity Notes")
        output = run_action(action, siemplify, {"Entity ID": "abc", "Entity Type": "Host"})

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
