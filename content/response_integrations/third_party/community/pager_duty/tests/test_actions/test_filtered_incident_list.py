from __future__ import annotations

import json

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from pager_duty.actions import FilteredIncidentList
from pager_duty.tests.common import CONFIG_PATH, MOCK_INCIDENTS_FILE
from pager_duty.tests.core.product import PagerDuty
from pager_duty.tests.core.session import PagerDutySession

DEFAULT_PARAMETERS: dict[str, str] = {
    "Incidents_Statuses": '["triggered", "acknowledged"]',
}


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_filtered_incident_list_success(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:

    mock_incidents = json.loads(MOCK_INCIDENTS_FILE.read_text())
    pagerduty.set_incidents(mock_incidents)
    success_output_msg = "Successfully retrieved Incidents\n"

    FilteredIncidentList.main()

    assert len(script_session.request_history) == 1
    assert action_output.report.output_message == success_output_msg
    assert action_output.report.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.report.result_value is True


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_filtered_incident_list_no_incidents_found(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """
    Tests the FilteredIncidentList action for the successful API call
    that returns no incidents.
    """
    pagerduty.set_incidents({})
    expected_output_msg = "Incidents not found\n"

    FilteredIncidentList.main()

    assert len(script_session.request_history) == 1
    assert action_output.report.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.report.result_value is True
    assert action_output.report.output_message == expected_output_msg
