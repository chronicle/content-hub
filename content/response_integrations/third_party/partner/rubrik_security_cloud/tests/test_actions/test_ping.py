from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from rubrik_security_cloud.actions import ping
from rubrik_security_cloud.tests.common import CONFIG_PATH, MOCK_CONNECTIVITY_RESPONSE
from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: RubrikSession,
        action_output: MockActionOutput,
        rubrik: RubrikSecurityCloud,
    ) -> None:
        rubrik.deployment_version = MOCK_CONNECTIVITY_RESPONSE["data"]["deploymentVersion"]
        success_output_msg = "Successfully connected to the Rubrik Security Cloud server!"

        ping.main()

        assert len(script_session.request_history) >= 1
        graphql_requests = [
            req
            for req in script_session.request_history
            if req.request.url.path.endswith("/api/graphql")
        ]
        assert len(graphql_requests) >= 1

        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
