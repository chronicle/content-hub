from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import (
    EXECUTION_STATE_COMPLETED,
)

from pager_duty.actions import Ping
from pager_duty.tests.common import CONFIG_PATH
from pager_duty.tests.core.session import PagerDutySession


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={},
)
def test_ping_success(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
) -> None:
    """
    Tests the Ping action for a successful connection.
    """
    Ping.main()
    assert len(script_session.request_history) == 1
    request = script_session.request_history[0].request
    assert request.url.path.endswith("/abilities")
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value is True
