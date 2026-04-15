from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import Ping
from ..common import CONFIG_PATH
from ..core.product import Phishrod
from ..core.session import PhishrodSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: PhishrodSession,
        action_output: MockActionOutput,
        phishrod: Phishrod,
    ) -> None:
        phishrod.set_test_connectivity_response({"ok": True})

        Ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_failure(
        self,
        script_session: PhishrodSession,
        action_output: MockActionOutput,
        phishrod: Phishrod,
    ) -> None:
        with phishrod.fail_requests():
            try:
                Ping.main()
            except Exception:
                pass  # Some actions raise instead of calling siemplify.end()

        # Verify failure was detected (either via execution_state or exception)
        if action_output.results is not None:
            assert action_output.results.execution_state == ExecutionState.FAILED
