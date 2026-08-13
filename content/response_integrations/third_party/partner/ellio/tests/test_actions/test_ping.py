from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ellio.actions import Ping
from ellio.tests.common import CONFIG_PATH
from ellio.tests.core.session import EllioSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: EllioSession,
        action_output: MockActionOutput,
    ) -> None:
        Ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully connected to the ELLIO server" in (
            action_output.results.output_message
        )
