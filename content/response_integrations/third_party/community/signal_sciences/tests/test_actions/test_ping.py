from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from signal_sciences.actions import Ping
from signal_sciences.tests.common import CONFIG_PATH
from signal_sciences.tests.core.product import SignalSciencesProduct
from signal_sciences.tests.core.session import SignalSciencesSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: SignalSciencesSession,
        action_output: MockActionOutput,
        signal_sciences: SignalSciencesProduct,
    ) -> None:
        # Add a mock site to ensure list_sites returns something
        signal_sciences.add_site({"name": "test_site"})

        Ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully connected" in action_output.results.output_message
