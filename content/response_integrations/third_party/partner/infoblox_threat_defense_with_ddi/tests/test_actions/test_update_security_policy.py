from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

UpdateSecurityPolicy = load_action("update_security_policy")


class TestUpdateSecurityPolicy:
    @set_metadata(
        parameters={"Security Policy ID": "1", "Policy Name": "renamed-policy"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_security_policies_response({
            "results": [
                {
                    "id": 1,
                    "name": "policy1",
                    "block_dns_rebind_attack": False,
                    "safe_search": False,
                    "network_lists": [],
                    "dfps": [],
                    "roaming_device_groups": [],
                    "rules": [],
                }
            ]
        })
        infoblox.set_update_security_policy_response({"results": {"id": 1, "name": "renamed-policy"}})

        UpdateSecurityPolicy.main()

        methods = {r.request.method.value for r in script_session.request_history}
        assert "GET" in methods
        assert "PUT" in methods
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully updated security policy with ID '1'" in action_output.results.output_message

    @set_metadata(parameters={"Security Policy ID": "1"}, integration_config_file_path=CONFIG_PATH)
    def test_policy_not_found_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_security_policies_response({"results": []})

        UpdateSecurityPolicy.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "not found" in action_output.results.output_message

    @set_metadata(parameters={"Security Policy ID": "not-an-int"}, integration_config_file_path=CONFIG_PATH)
    def test_invalid_id_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        UpdateSecurityPolicy.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(parameters={"Security Policy ID": "1"}, integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            UpdateSecurityPolicy.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
