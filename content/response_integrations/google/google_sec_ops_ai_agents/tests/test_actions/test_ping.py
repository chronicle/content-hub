from __future__ import annotations
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from google_sec_ops_ai_agents.actions import ping
from google_sec_ops_ai_agents.tests import common
from google_sec_ops_ai_agents.tests.core.product import GoogleSecOpsAiAgents
from google_sec_ops_ai_agents.tests.core.session import GoogleSecOpsAiAgentsSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

@set_metadata(integration_config=common.CONFIG)
def test_ping_success(
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
    script_session: GoogleSecOpsAiAgentsSession,
    action_output: MockActionOutput,
) -> None:
    google_chronicle_ai_agents.cleanup_investigations()
    google_chronicle_ai_agents.add_investigations("siemplify-connectivity-test", [{"name": "test"}])
    ping.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=ping.SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )
