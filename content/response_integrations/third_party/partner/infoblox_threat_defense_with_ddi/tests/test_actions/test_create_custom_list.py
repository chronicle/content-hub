from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

CreateCustomList = load_action("create_custom_list")


class TestCreateCustomList:
    @set_metadata(
        parameters={"Name": "blocklist", "Type": "custom_list", "Items": "evil.com, 10.0.0.5"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_create_custom_list_response({"results": {"id": 1, "name": "blocklist"}})

        CreateCustomList.main()

        assert any(
            r.request.method.value == "POST" and r.request.url.path.endswith("/api/atcfw/v1/named_lists")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully created custom list 'blocklist'" in action_output.results.output_message

    @set_metadata(
        parameters={"Name": "blocklist", "Type": "custom_list", "Items": "not_a_valid_item!!"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_invalid_items_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        CreateCustomList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False

    @set_metadata(
        parameters={"Name": "blocklist", "Type": "custom_list"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            CreateCustomList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
