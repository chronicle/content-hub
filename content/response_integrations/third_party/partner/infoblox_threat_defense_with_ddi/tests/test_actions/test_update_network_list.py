from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

UpdateNetworkList = load_action("update_network_list")


class TestUpdateNetworkList:
    @set_metadata(
        parameters={"Network List ID": "5", "Name": "renamed-net"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_network_list_by_id_response({
            "results": {"id": 5, "name": "net1", "items": ["10.0.0.0/24"], "description": "d"}
        })
        infoblox.set_update_network_list_response({
            "results": {"id": 5, "name": "renamed-net", "items": ["10.0.0.0/24"], "description": "d"}
        })

        UpdateNetworkList.main()

        methods = {r.request.method.value for r in script_session.request_history}
        assert "GET" in methods
        assert "PUT" in methods
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully updated network list with ID '5'" in action_output.results.output_message

    @set_metadata(parameters={"Network List ID": "not-an-int"}, integration_config_file_path=CONFIG_PATH)
    def test_invalid_id_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        UpdateNetworkList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(parameters={"Network List ID": "5"}, integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            UpdateNetworkList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
