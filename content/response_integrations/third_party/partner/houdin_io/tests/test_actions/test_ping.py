from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from houdin_io.actions import ping
from houdin_io.tests.common import CONFIG_PATH
from houdin_io.tests.mock_session import HoudinSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_valid_key(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.output_message
            == "Successfully connected to the Houdin-io server with the provided connection parameters!"
        )
        request = houdin.request_history[0].request
        assert request.url.path == "/api/v1/ping"
        assert request.headers["X-API-Key"] == "test-api-key"

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_rejected_key(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        houdin.key_valid = False

        ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.output_message.startswith("Failed to connect to the Houdin-io server!")
        assert "Invalid API Key" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_server_error_is_retried(self, houdin: HoudinSession, action_output: MockActionOutput) -> None:
        houdin.server_errors_left = 1

        ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert len(houdin.request_history) == 2
