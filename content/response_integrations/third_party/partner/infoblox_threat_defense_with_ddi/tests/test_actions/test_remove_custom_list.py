from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

RemoveCustomList = load_action("remove_custom_list")


class TestRemoveCustomList:
    @set_metadata(parameters={"Custom List ID": "1"}, integration_config_file_path=CONFIG_PATH)
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        RemoveCustomList.main()

        assert any(
            r.request.method.value == "DELETE" and r.request.url.path.endswith("/api/atcfw/v1/named_lists/1")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully removed the custom list with ID 1" in action_output.results.output_message

    @set_metadata(parameters={"Custom List ID": "not-an-int"}, integration_config_file_path=CONFIG_PATH)
    def test_invalid_id_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        RemoveCustomList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(parameters={"Custom List ID": "1"}, integration_config_file_path=CONFIG_PATH)
    def test_api_failure_not_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=404, body={"error": [{"message": "List not found"}]}):
            RemoveCustomList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "List not found" in action_output.results.output_message
