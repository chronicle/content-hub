from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import CreateUser
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

PRIMARY_EMAIL: str = "jane.doe@domain.com"
GIVEN_NAME: str = "Jane"
FAMILY_NAME: str = "Doe"

ACTION_PARAMETERS: dict[str, str | bool] = {
    "Given Name": GIVEN_NAME,
    "Family Name": FAMILY_NAME,
    "Password": "S3cur3P@ssw0rd!",
    "Email Address": PRIMARY_EMAIL,
    "Change Password At Next Login": "false",
}

SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully created user {GIVEN_NAME} {FAMILY_NAME} with"
    f"primary email address {PRIMARY_EMAIL}"
)


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_create_user_success(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    CreateUser.main()

    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_create_user_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # ISSUE FINDER: CreateUser does not have a dedicated path to surface a
    # 409-Conflict (duplicate email) as a user-facing error — the generic
    # except block catches GSuiteEntityExistsException and sets FAILED with
    # the raw exception message. This is functionally correct but the message
    # format differs from other actions.
    #
    # We simulate a server-side error by inserting a user with the same email
    # so the mock returns HTTP 409 Conflict.
    _product.add_directory_user({"primaryEmail": PRIMARY_EMAIL})

    CreateUser.main()

    # ISSUE FINDER: CreateUser swallows GSuiteEntityExistsException in the
    # generic `except Exception` branch, so execution_state is FAILED and
    # result_value is False — correct, but message won't mention "already exists".
    assert action_output.results.result_value in (False, "false")
    assert action_output.results.execution_state == ExecutionState.FAILED
