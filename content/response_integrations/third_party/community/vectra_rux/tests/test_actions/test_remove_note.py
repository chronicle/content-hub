from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Entity ID": "68599", "Note ID": "9118", "Entity Type": "Host"}


class TestRemoveNote:
    def test_remove_note_success(self, siemplify, mock_session, product):
        action = load_action("Remove Note")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert 'Successfully deleted note "9118" from host with ID "68599"' in output.output_message

    def test_remove_note_invalid_note_id(self, siemplify, mock_session, product):
        action = load_action("Remove Note")
        params = dict(DEFAULT_PARAMETERS)
        params["Note ID"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_remove_note_not_found(self, siemplify, mock_session, product):
        product.fail("REMOVE_NOTE", 404, {"detail": "Entity ID or Note ID does not exist"})
        action = load_action("Remove Note")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
