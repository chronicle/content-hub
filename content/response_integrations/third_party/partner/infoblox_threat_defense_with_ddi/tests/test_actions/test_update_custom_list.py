from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

UpdateCustomList = load_action("update_custom_list")


class TestUpdateCustomList:
    @set_metadata(
        parameters={"Custom List ID": "1", "Name": "renamed-list"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_custom_list_by_id_response({
            "results": {
                "id": 1,
                "name": "renamed-list",
                "description": "d",
                "confidence_level": "HIGH",
                "threat_level": "LOW",
                "items": [],
            }
        })

        UpdateCustomList.main()

        methods = {r.request.method.value for r in script_session.request_history}
        assert "GET" in methods
        assert "PUT" in methods
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully updated custom list with ID '1'" in action_output.results.output_message

    @set_metadata(
        parameters={"Custom List ID": "not-an-int"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_invalid_id_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        UpdateCustomList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        parameters={"Custom List ID": "1"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            UpdateCustomList.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
