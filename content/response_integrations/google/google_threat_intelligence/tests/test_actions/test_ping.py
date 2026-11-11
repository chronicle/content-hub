from __future__ import annotations

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from google_threat_intelligence.actions import ping
from google_threat_intelligence.tests.common import CONFIG_PATH
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

PING_SUCCESS_MESSAGE: str = (
    "Successfully connected to the Google Threat Intelligence "
    "server with the provided connection parameters!"
)


@set_metadata(integration_config_file_path=CONFIG_PATH)
def test_ping(
    script_session: GoogleThreatIntelligenceSession,
    action_output: MockActionOutput,
) -> None:

    ping.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=PING_SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
        debug_output="",
    )
