from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from pager_duty.actions import CreateIncident
from pager_duty.tests.common import CONFIG_PATH
from pager_duty.tests.core.session import PagerDutySession

EXPECTED_SUCCESS_OUTPUT_MSG = "Successfully Created Incident\n"
EXPECTED_FAILED_OUTPUT_MSG = "There was an error creating a new incident."


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Email": "test@example.com",
        "Title": "Test Incident",
        "Urgency": "high",
        "Details": "Test Details",
    },
)
def test_create_incident_success(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
) -> None:
    """Tests the CreateIncident action for a successful API call."""
    CreateIncident.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value == "true"
    assert action_output.results.output_message == EXPECTED_SUCCESS_OUTPUT_MSG


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Email": "",
        "Title": "Test Incident",
        "Urgency": "high",
        "Details": "Test Details",
    },
)
def test_create_incident_failed(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
) -> None:
    """Tests the CreateIncident action when an error occurs during incident creation."""
    CreateIncident.main()

    assert action_output.results.execution_state.value == EXECUTION_STATE_FAILED
    assert action_output.results.result_value is False
    assert EXPECTED_FAILED_OUTPUT_MSG in action_output.results.output_message
