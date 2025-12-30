from __future__ import annotations

import json
import pathlib

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED

from pager_duty.actions import ListUsers
from pager_duty.tests.common import CONFIG_PATH, INTEGRATION_PATH
from pager_duty.tests.core.product import PagerDuty
from pager_duty.tests.core.session import PagerDutySession

MOCK_USERS_FILE: pathlib.Path = INTEGRATION_PATH / "tests" / "mocks" / "users.json"


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={},
)
def test_list_users_success(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """Tests the ListUsers action for a successful API call."""
    # Arrange
    mock_users = json.loads(MOCK_USERS_FILE.read_text())
    pagerduty.set_users(mock_users)
    success_output_msg = "Successfully retrieved users\n"

    ListUsers.main()

    assert len(script_session.request_history) == 1
    request = script_session.request_history[0].request
    assert request.url.path.endswith("/users")
    assert action_output.report.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.report.result_value is True
    assert action_output.report.output_message == success_output_msg


@set_metadata(
    integration_config_file_path=CONFIG_PATH,
    parameters={},
)
def test_list_users_no_users_found(
    script_session: PagerDutySession,
    action_output: MockActionOutput,
    pagerduty: PagerDuty,
) -> None:
    """Tests the ListUsers action for a successful API call that returns no users."""

    pagerduty.set_users({})
    expected_output_msg = "no users found\n"

    ListUsers.main()

    assert len(script_session.request_history) == 1
    request = script_session.request_history[0].request
    assert request.url.path.endswith("/users")
    assert action_output.report.execution_state.value == EXECUTION_STATE_COMPLETED
    assert action_output.report.result_value is True
    assert action_output.report.output_message == expected_output_msg
