from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

UpdateCustomListItems = load_action("update_custom_list_items")


class TestUpdateCustomListItems:
    @set_metadata(
        parameters={"Custom List ID": "1", "Action": "Add", "Items": "evil.com, 10.0.0.5"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success_add(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_update_custom_list_items_response({
            "inserted_items": ["evil.com", "10.0.0.5"],
            "deleted_items": [],
            "updated_items": [],
        })

        UpdateCustomListItems.main()

        assert any(
            r.request.method.value == "PATCH" and r.request.url.path.endswith("/api/atcfw/v1/named_lists/1/items")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Added: 2" in action_output.results.output_message

    @set_metadata(
        parameters={"Custom List ID": "1", "Action": "Remove", "Items": " , ,"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_empty_items_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        UpdateCustomListItems.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "must not be empty" in action_output.results.output_message

    @set_metadata(
        parameters={"Custom List ID": "1", "Action": "Add", "Items": "not_valid!!"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_invalid_indicator_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        UpdateCustomListItems.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        parameters={"Custom List ID": "1", "Action": "Add", "Items": "evil.com"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            UpdateCustomListItems.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
