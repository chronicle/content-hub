from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from signal_sciences.actions import Ping
from signal_sciences.tests.common import CONFIG_PATH
from signal_sciences.tests.core.product import SignalSciences
from signal_sciences.tests.core.session import SignalSciencesSession


class TestPing:
    @set_metadata(
        parameters={},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_ping_success(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciences,
    ) -> None:
        # Arrange
        signal_sciences.add_corp("test-corp", {"name": "test-corp"})
        success_output_msg = (
            "Successfully connected to the Signal Sciences server with the "
            "provided connection parameters!"
        )

        # Act
        Ping.main()

        # Assert
        assert len(script_session.request_history) == 1
        request = script_session.request_history[0].request
        assert request.method.value == "GET"
        assert request.url.path.endswith("/corps/test-corp")

        assert success_output_msg in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
