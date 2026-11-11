from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import UpdateUser
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

PRIMARY_EMAIL: str = "john.smith@domain.com"
GIVEN_NAME: str = "John"
FAMILY_NAME: str = "Smith"

ACTION_PARAMETERS: dict[str, str | bool] = {
    "Email Address": PRIMARY_EMAIL,
    "Given Name": GIVEN_NAME,
    "Family Name": FAMILY_NAME,
    "Change Password At Next Login": "false",
    "User Status": "Not Changed",
}

SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully updated the following users in Google Workspace: {PRIMARY_EMAIL}"
)
NONE_UPDATED_MESSAGE: str = "None of the provided users were updated."

CONFIG_WITHOUT_CREDS: dict = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_update_user_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_directory_user(
        {
            "primaryEmail": PRIMARY_EMAIL,
            "name": {"givenName": "Old", "familyName": "Name"},
            "id": "user-id-1",
            "kind": "admin#directory#user",
        }
    )

    UpdateUser.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_update_user_not_found(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No user seeded — update should fail per-user and report none updated.
    UpdateUser.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == NONE_UPDATED_MESSAGE
    # ISSUE FINDER: UpdateUser returns result_value=False and
    # EXECUTION_STATE_COMPLETED (not FAILED) when all users fail to update.
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG_WITHOUT_CREDS, parameters=ACTION_PARAMETERS)
def test_update_user_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No credentials → auth manager raises before any HTTP call
    UpdateUser.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
