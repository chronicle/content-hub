from __future__ import annotations

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from splunk.actions import Ping
from splunk.core.constants import INTEGRATION_NAME
from splunk.tests.const import CONFIG_PATH
from splunk.tests.core.session import SplunkSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


PING_SUCCESS_MESSAGE: str = (
    f"Successfully connected to the {INTEGRATION_NAME} "
    "server with the provided connection parameters!."
)
PING_ENDPOINT: str = "/:/services/search/v2/jobs/export"


@set_metadata(integration_config_file_path=CONFIG_PATH)
def test_default_parameters_succeeds(
    script_session: SplunkSession,
    action_output: MockActionOutput,
) -> None:
    Ping.main()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[-1].request.real_url == PING_ENDPOINT
    assert action_output.results == ActionOutput(
        output_message=PING_SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )
