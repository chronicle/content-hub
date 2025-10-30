from __future__ import annotations

import json

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from pager_duty.actions import GetIncidentById
from pager_duty.tests.common import CONFIG_PATH, MOCK_INCIDENTS_FILE
from pager_duty.tests.core.product import PagerDuty
from pager_duty.tests.core.session import PagerDutySession

SUCCESS_INCIDENT_KEY = "65245cf57ed7427a84e64b418049b78f"
INVALID_INCIDENT_KEY = "invalid_incident_key"
DEFAULT_PARAMETERS: dict[str, str] = {
    "Incident Key": SUCCESS_INCIDENT_KEY,
    "Email": "test@example.com",
}


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_get_incident_by_id_success(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """Tests the GetIncidentById action for a successful API call."""

    mock_incidents = json.loads(MOCK_INCIDENTS_FILE.read_text())
    pagerduty.set_incidents(mock_incidents)

    GetIncidentById.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value is True
    assert "Successfully retrieved Incident" in action_output.results.output_message


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Incident Key": INVALID_INCIDENT_KEY,
        "Email": "test@example.com",
    },
)
def test_get_incident_by_id_not_found(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """Tests the GetIncidentById action when no incident is found for the key."""

    mock_incidents = json.loads(MOCK_INCIDENTS_FILE.read_text())
    pagerduty.set_incidents(mock_incidents)

    GetIncidentById.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value is True
    assert "No Incident Found" in action_output.results.output_message
