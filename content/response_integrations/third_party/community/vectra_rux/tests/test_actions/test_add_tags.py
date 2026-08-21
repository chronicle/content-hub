from __future__ import annotations

from ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from tests.common import load_action
from tests.conftest import run_action

DEFAULT_PARAMETERS = {"Tags": "test-tag", "Entity IDs": "103", "Entity Type": "Account"}


class TestAddTags:
    def test_add_tags_success(self, siemplify, mock_session, product):
        action = load_action("Add Tags")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is True
        assert output.execution_state == EXECUTION_STATE_COMPLETED
        assert 'Successfully added tag(s) to account(s): "103"' in output.output_message

    def test_add_tags_invalid_entity_id(self, siemplify, mock_session, product):
        action = load_action("Add Tags")
        params = dict(DEFAULT_PARAMETERS)
        params["Entity IDs"] = "abc"
        output = run_action(action, siemplify, params)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED

    def test_add_tags_entity_not_found(self, siemplify, mock_session, product):
        product.list_tags_response = None
        product.fail("LIST_TAGS", 404, {"message": "not found", "status": "failed"})
        action = load_action("Add Tags")
        output = run_action(action, siemplify, DEFAULT_PARAMETERS)

        assert output.result_value is False
        assert output.execution_state == EXECUTION_STATE_FAILED
        assert "Failed to add tag(s)" in output.output_message
