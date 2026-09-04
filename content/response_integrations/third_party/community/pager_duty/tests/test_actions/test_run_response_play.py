from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from pager_duty.actions import RunResponsePlay
from pager_duty.tests.common import CONFIG_PATH
from pager_duty.tests.core.session import PagerDutySession

EXPECTED_SUCCESS_OUTPUT_MSG = "The response was Successfully runed "
EXPECTED_FAILED_OUTPUT_MSG = "There is no response in the incident ."


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Email": "user@example.com",
        "Response ID": "RP12345",
        "Incident_ID": "INC12345",
    },
)
def test_run_response_play_success(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
) -> None:
    """Tests the RunResponsePlay action for a successful API call."""
    RunResponsePlay.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.output_message == EXPECTED_SUCCESS_OUTPUT_MSG


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Email": "user@example.com",
        "Response ID": "INVALID_PLAY_ID",
        "Incident_ID": "INC12345",
    },
)
def test_run_response_play_failed(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
) -> None:
    """Tests the RunResponsePlay action when the response play fails."""
    RunResponsePlay.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_FAILED
    assert action_output.results.result_value is False
    assert EXPECTED_FAILED_OUTPUT_MSG in action_output.results.output_message
