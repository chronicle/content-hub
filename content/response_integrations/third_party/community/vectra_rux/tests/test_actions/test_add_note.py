from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Note": "This is test note", "Entity ID": "68599", "Entity Type": "Host"}


class TestAddNote:
    def test_add_note_success(self, siemplify, mock_session, product):
        action = load_action("Add Note")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert 'Successfully added note to host with ID "68599"' in output.output_message
        assert len(siemplify.result.data_tables) == 1

    def test_add_note_invalid_entity_id(self, siemplify, mock_session, product):
        action = load_action("Add Note")
        params = dict(DEFAULT_PARAMETERS)
        params["Entity ID"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_add_note_entity_not_found(self, siemplify, mock_session, product):
        product.fail("ADD_NOTE", 404, {"detail": "Entity ID or Note ID does not exist"})
        action = load_action("Add Note")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
