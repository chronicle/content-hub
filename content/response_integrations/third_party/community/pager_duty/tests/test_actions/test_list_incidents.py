from __future__ import annotations

import json

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from pager_duty.actions import ListIncidents
from pager_duty.tests.common import CONFIG_PATH, MOCK_INCIDENTS_FILE
from pager_duty.tests.core.product import PagerDuty
from pager_duty.tests.core.session import PagerDutySession

EXPECTED_SUCCESS_OUTPUT_MSG = "Successfully retrieved Incidents\n"
EXPECTED_NOT_FOUND_OUTPUT_MSG = "Incidents not found\n"


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={},
)
def test_list_incidents_success(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """Tests the ListIncidents action for a successful API call."""
    mock_incidents = json.loads(MOCK_INCIDENTS_FILE.read_text())
    pagerduty.set_incidents(mock_incidents)

    ListIncidents.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.output_message == EXPECTED_SUCCESS_OUTPUT_MSG


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={},
)
def test_list_incidents_not_found(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """Tests the ListIncidents action when no incidents are found."""
    pagerduty.set_incidents({})

    ListIncidents.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value is True
    assert action_output.results.output_message == EXPECTED_NOT_FOUND_OUTPUT_MSG
