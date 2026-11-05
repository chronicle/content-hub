from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {
    "Entity ID": "68599",
    "Entity Type": "Host",
    "Note ID": "9118",
    "Note": "This is an updated test note",
}


class TestUpdateEntityNote:
    def test_update_entity_note_success(self, siemplify, mock_session, product):
        action = load_action("Update Entity Note")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert output.output_message == "The note has been successfully updated in the entity"

    def test_update_entity_note_invalid_note_id(self, siemplify, mock_session, product):
        action = load_action("Update Entity Note")
        params = dict(DEFAULT_PARAMETERS)
        params["Note ID"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_update_entity_note_api_error(self, siemplify, mock_session, product):
        product.fail("UPDATE_ENTITY_NOTE", 403, {"detail": "User not permitted to perform this action"})
        action = load_action("Update Entity Note")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
