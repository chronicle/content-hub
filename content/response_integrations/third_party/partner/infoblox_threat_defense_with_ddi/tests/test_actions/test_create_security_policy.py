from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ..common import CONFIG_PATH, load_action
from ..core.product import Infoblox
from ..core.session import InfobloxSession

CreateSecurityPolicy = load_action("create_security_policy")


class TestCreateSecurityPolicy:
    @set_metadata(
        parameters={"Policy Name": "policy1", "Network Lists": "1, 2"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_success(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        infoblox.set_create_security_policy_response({"results": {"id": 1, "name": "policy1"}})

        CreateSecurityPolicy.main()

        assert any(
            r.request.method.value == "POST" and r.request.url.path.endswith("/api/atcfw/v1/security_policies")
            for r in script_session.request_history
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully created security policy 'policy1'" in action_output.results.output_message

    @set_metadata(
        parameters={"Policy Name": "policy1", "Rules": "not-json"},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_invalid_rules_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        CreateSecurityPolicy.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        parameters={"Policy Name": "policy1", "Additional Parameters": '{"bogus_key": 1}'},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_unsupported_additional_param_fails(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        CreateSecurityPolicy.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Unsupported key" in action_output.results.output_message

    @set_metadata(parameters={"Policy Name": "policy1"}, integration_config_file_path=CONFIG_PATH)
    def test_api_failure(
        self,
        script_session: InfobloxSession,
        action_output: MockActionOutput,
        infoblox: Infoblox,
    ) -> None:
        with infoblox.fail_requests(status_code=500):
            CreateSecurityPolicy.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
