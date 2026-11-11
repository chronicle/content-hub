from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import ListUsers
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

MOCK_USERS: list[dict] = [
    {
        "primaryEmail": "alice@domain.com",
        "name": {"givenName": "Alice", "familyName": "Example"},
        "id": "uid-1",
        "kind": "admin#directory#user",
        "isAdmin": False,
        "isDelegatedAdmin": False,
        "suspended": False,
        "isEnrolledIn2Sv": True,
    },
    {
        "primaryEmail": "bob@domain.com",
        "name": {"givenName": "Bob", "familyName": "Example"},
        "id": "uid-2",
        "kind": "admin#directory#user",
        "isAdmin": False,
        "isDelegatedAdmin": False,
        "suspended": False,
        "isEnrolledIn2Sv": True,
    },
]

ACTION_PARAMETERS: dict[str, str | int | bool] = {
    "Customer ID": "my_customer",
    "Record Limit": 50,
    "Return only Admin Accounts?": False,
    "Return only Delegated Admin Accounts?": False,
    "Return only Suspended Users?": False,
    "Return only users without 2fa?": False,
}

NO_USERS_OUTPUT_MESSAGE: str = "No users were returned."

CONFIG_WITHOUT_CREDS: dict = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_users_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_directory_users(MOCK_USERS)

    ListUsers.main()

    assert len(script_session.request_history) > 0
    # ISSUE FINDER: ListUsers output message has a missing space — the f-string
    # concatenates without a space: f"Action successfully returned {INTEGRATION_NAME}"
    # + "Directory user list" → "returned GSuiteDirectory user list".
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_users_no_results(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_directory_users([])

    ListUsers.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == NO_USERS_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG_WITHOUT_CREDS, parameters=ACTION_PARAMETERS)
def test_list_users_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No credentials → auth manager raises before any HTTP call
    ListUsers.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
