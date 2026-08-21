from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

GetSecurityPolicies = load_action("get_security_policies")


class TestGetSecurityPolicies:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_security_policies_response({"results": [{"id": 1, "name": "policy1"}]})

        GetSecurityPolicies.main()

        assert any(
            r.request.url.path.endswith("/api/atcfw/v1/security_policies") for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully retrieved 1 security policy" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_no_policies_found(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_security_policies_response({"results": []})

        GetSecurityPolicies.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == "No security policies found."

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            GetSecurityPolicies.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
