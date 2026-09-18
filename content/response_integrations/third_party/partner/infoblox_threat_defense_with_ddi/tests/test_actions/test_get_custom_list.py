from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

GetCustomList = load_action("get_custom_list")


class TestGetCustomList:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_success_base_listing(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_custom_list_response({"results": [{"id": 1, "name": "blocklist"}]})

        GetCustomList.main()

        assert any(r.request.url.path.endswith("/api/atcfw/v1/named_lists") for r in script_session.request_history)
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 custom list" in action_output.results.output_message

    @set_metadata(parameters={"Custom List ID": "1"}, integration_config_file_path=CONFIG_PATH)
    def test_success_by_id(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_custom_list_by_id_response({"results": {"id": 1, "name": "blocklist"}})

        GetCustomList.main()

        assert any(r.request.url.path.endswith("/api/atcfw/v1/named_lists/1") for r in script_session.request_history)
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(parameters={"Custom List ID": "not-an-int"}, integration_config_file_path=CONFIG_PATH)
    def test_invalid_id_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        GetCustomList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_no_lists_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_custom_list_response({"results": []})

        GetCustomList.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == "No custom lists found."

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            GetCustomList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
