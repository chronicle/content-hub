from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

RemoveSecurityPolicy = load_action("remove_security_policy")


class TestRemoveSecurityPolicy:
    @set_metadata(parameters={"Security Policy ID": "1"}, integration_config_file_path=CONFIG_PATH)
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        RemoveSecurityPolicy.main()

        assert any(
            r.request.method.value == "DELETE" and r.request.url.path.endswith("/api/atcfw/v1/security_policies/1")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully removed security policy with ID '1'" in action_output.results.output_message

    @set_metadata(parameters={"Security Policy ID": "not-an-int"}, integration_config_file_path=CONFIG_PATH)
    def test_invalid_id_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        RemoveSecurityPolicy.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(parameters={"Security Policy ID": "1"}, integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            RemoveSecurityPolicy.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
