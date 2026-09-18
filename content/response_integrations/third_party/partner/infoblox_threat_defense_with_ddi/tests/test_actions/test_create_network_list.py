from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

CreateNetworkList = load_action("create_network_list")


class TestCreateNetworkList:
    @set_metadata(
        parameters={"Name": "net1", "Items": "10.0.0.0/24, 10.0.1.0/24"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_create_network_list_response({"results": {"id": 5, "name": "net1"}})

        CreateNetworkList.main()

        assert any(
            r.request.method.value == "POST" and r.request.url.path.endswith("/api/atcfw/v1/network_lists")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully created network list 'net1'" in action_output.results.output_message

    @set_metadata(
        parameters={"Name": "net1", "Items": "10.0.0.0/24"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            CreateNetworkList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
