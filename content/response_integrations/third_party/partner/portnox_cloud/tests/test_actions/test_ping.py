from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import ping
from ..common import CONFIG_PATH
from ..core.product import PortnoxCloud
from ..core.session import PortnoxCloudSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_with_valid_token_succeeds(
        self,
        script_session: PortnoxCloudSession,
        action_output: MockActionOutput,
    ) -> None:
        ping.main()

        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.url.path.endswith("/api/device/list")
        assert request.kwargs["headers"] == {"Authorization": "test_api_token"}
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.output_message == (
            "Successfully connected to the Portnox Cloud server with the provided connection parameters!"
        )

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_with_rejected_token_fails(
        self,
        action_output: MockActionOutput,
        portnox: PortnoxCloud,
    ) -> None:
        with portnox.fail_requests(status_code=401):
            ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert action_output.results.output_message.startswith(
            "Failed to connect to the Portnox Cloud server! Error is Portnox Cloud rejected the credentials"
        )

    @set_metadata(integration_config={"API Root": "https://portnox.example.com/CloudPortalBackEnd/"})
    def test_ping_without_credentials_fails_before_calling_api(
        self,
        script_session: PortnoxCloudSession,
        action_output: MockActionOutput,
    ) -> None:
        ping.main()

        assert not script_session.request_history
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Provide either an API Token or a local admin Username and Password" in (
            action_output.results.output_message
        )
