from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

GetNetworkList = load_action("get_network_list")


class TestGetNetworkList:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_success_base_listing(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_network_list_response({"results": [{"id": 5, "name": "net1"}]})

        GetNetworkList.main()

        assert any(r.request.url.path.endswith("/api/atcfw/v1/network_lists") for r in script_session.request_history)
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 network list" in action_output.results.output_message

    @set_metadata(parameters={"Network List ID": "5"}, integration_config_file_path=CONFIG_PATH)
    def test_success_by_id(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_network_list_by_id_response({"results": {"id": 5, "name": "net1"}})

        GetNetworkList.main()

        assert any(r.request.url.path.endswith("/api/atcfw/v1/network_lists/5") for r in script_session.request_history)
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(parameters={"Network List ID": "not-an-int"}, integration_config_file_path=CONFIG_PATH)
    def test_invalid_id_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        GetNetworkList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_no_lists_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_network_list_response({"results": []})

        GetNetworkList.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == "No network lists found."

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            GetNetworkList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
