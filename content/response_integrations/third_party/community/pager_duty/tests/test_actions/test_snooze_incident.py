from __future__ import annotations

import json

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from pager_duty.actions import SnoozeIncident
from pager_duty.tests.common import CONFIG_PATH, MOCK_INCIDENTS_FILE
from pager_duty.tests.core.product import PagerDuty
from pager_duty.tests.core.session import PagerDutySession

VALID_INCIDENT_ID = "Q3SN8FBZ4LBON7"
INVALID_INCIDENT_ID = "NONEXISTENT_INCIDENT"
TEST_EMAIL = "test@example.com"

DEFAULT_PARAMETERS: dict[str, str] = {
    "Email": TEST_EMAIL,
    "IncidentID": VALID_INCIDENT_ID,
}


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_snooze_incident_success(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """Tests the SnoozeIncident action for a successful API call."""

    mock_incidents = json.loads(MOCK_INCIDENTS_FILE.read_text())
    mock_incidents["incidents"][0]["status"] = "acknowledged"
    pagerduty.set_incidents(mock_incidents)
    success_output_msg = "Successfully Snoozed Incident\n"

    SnoozeIncident.main()

    assert len(script_session.request_history) == 1
    assert action_output.report.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.report.result_value is True
    assert action_output.report.output_message == success_output_msg


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Email": TEST_EMAIL,
        "IncidentID": INVALID_INCIDENT_ID,
    },
)
def test_snooze_incident_not_found(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """Tests the SnoozeIncident action when the incident is not found."""

    mock_incidents = json.loads(MOCK_INCIDENTS_FILE.read_text())
    pagerduty.set_incidents(mock_incidents)
    expected_output_msg = "Incident wasnt snoozed\nPagerDuty API error: 404 None"

    SnoozeIncident.main()

    assert len(script_session.request_history) == 1
    assert action_output.report.execution_state.value == EXECUTION_STATE_FAILED
    assert action_output.report.result_value is False
    assert expected_output_msg in action_output.report.output_message
