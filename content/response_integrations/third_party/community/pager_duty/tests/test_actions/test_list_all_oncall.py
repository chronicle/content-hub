from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from pager_duty.actions import ListAllOncall
from pager_duty.tests.common import CONFIG_PATH
from pager_duty.tests.core.session import PagerDutySession

EXPECTED_SUCCESS_OUTPUT_MSG = "Successfully retrieved users\n"
EXPECTED_FAILED_OUTPUT_MSG = "There is no OnCall List."


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={},
)
def test_list_all_oncall_success(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
) -> None:
    """Tests the ListAllOncall action for a successful API call."""
    ListAllOncall.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.output_message == EXPECTED_SUCCESS_OUTPUT_MSG
