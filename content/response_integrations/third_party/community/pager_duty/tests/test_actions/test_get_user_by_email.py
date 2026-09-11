from __future__ import annotations

import json
import pathlib

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED

from pager_duty.actions import GetUserByEmail
from pager_duty.tests.common import CONFIG_PATH, INTEGRATION_PATH
from pager_duty.tests.core.product import PagerDuty
from pager_duty.tests.core.session import PagerDutySession

EXPECTED_SUCCESS_OUTPUT_MSG = "Successfully retrieved user"
EXPECTED_FAILED_OUTPUT_MSG = "There is no user with this Email"

MOCK_USERS_FILE: pathlib.Path = INTEGRATION_PATH / "tests" / "mocks" / "users.json"


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Email": "john.doe@example.com",
    },
)
def test_get_user_by_email_success(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """Tests the GetUserByEmail action for a successful API call."""
    mock_users = json.loads(MOCK_USERS_FILE.read_text())
    pagerduty.set_users(mock_users)

    GetUserByEmail.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.results.result_value is True
    assert EXPECTED_SUCCESS_OUTPUT_MSG in action_output.results.output_message


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={
        "Email": "nonexistent@example.com",
    },
)
def test_get_user_by_email_failed(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """Tests the GetUserByEmail action when the user is not found."""
    mock_users = json.loads(MOCK_USERS_FILE.read_text())
    pagerduty.set_users(mock_users)

    GetUserByEmail.main()

    assert len(script_session.request_history) == 1
    assert action_output.results.execution_state.value == EXECUTION_STATE_FAILED
    assert action_output.results.result_value is False
    assert EXPECTED_FAILED_OUTPUT_MSG in action_output.results.output_message
