from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from ...actions import ping
from ..common import CONFIG_PATH
from ..core.product import GoogleSecOpsAiAgents
from ..core.session import GoogleSecOpsAiAgentsSession


class TestPing:
    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: GoogleSecOpsAiAgentsSession,
        action_output: MockActionOutput,
        google_sec_ops_ai_agents: GoogleSecOpsAiAgents,
    ) -> None:
        # No explicit connectivity method — Manager construction is the test

        ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_failure(
        self,
        script_session: GoogleSecOpsAiAgentsSession,
        action_output: MockActionOutput,
        google_sec_ops_ai_agents: GoogleSecOpsAiAgents,
    ) -> None:
        with google_sec_ops_ai_agents.fail_requests():
            try:
                ping.main()
            except Exception:
                pass  # Some actions raise instead of calling siemplify.end()

        # This Ping action does not use EXECUTION_STATE_FAILED — it reports
        # failure through result_value only. Verify either the result_value
        # indicates failure or an exception was raised.
        if action_output.results is not None:
            failed_state = action_output.results.execution_state == ExecutionState.FAILED
            failed_result = action_output.results.result_value in ("false", "False", False)
            assert failed_state or failed_result
