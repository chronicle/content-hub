from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

RemoveNetworkList = load_action("remove_network_list")


class TestRemoveNetworkList:
    @set_metadata(parameters={"Network List ID": "5"}, integration_config_file_path=CONFIG_PATH)
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        RemoveNetworkList.main()

        assert any(
            r.request.method.value == "DELETE" and r.request.url.path.endswith("/api/atcfw/v1/network_lists/5")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully removed network list with ID '5'" in action_output.results.output_message

    @set_metadata(parameters={"Network List ID": "not-an-int"}, integration_config_file_path=CONFIG_PATH)
    def test_invalid_id_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        RemoveNetworkList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(parameters={"Network List ID": "5"}, integration_config_file_path=CONFIG_PATH)
    def test_api_failure_conflict(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(
            status_code=409, body={"error": [{"message": "Network list assigned to a policy"}]}
        ):
            RemoveNetworkList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "assigned to a policy" in action_output.results.output_message
