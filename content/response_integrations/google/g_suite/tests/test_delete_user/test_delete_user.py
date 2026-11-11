from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import DeleteUser
from g_suite.core.consts import DELETE_USER_SCRIPT_NAME
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

PRIMARY_EMAIL: str = "todelete@domain.com"

ACTION_PARAMETERS: dict[str, str] = {
    "Email Address": PRIMARY_EMAIL,
}

SUCCESS_OUTPUT_MESSAGE: str = f"Successfully deleted user {PRIMARY_EMAIL}"
NOT_FOUND_OUTPUT_MESSAGE: str = (
    f"Error executing action {DELETE_USER_SCRIPT_NAME}. Reason: User not found"
)

CONFIG_WITHOUT_CREDS: dict = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_delete_user_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_directory_user(
        {
            "primaryEmail": PRIMARY_EMAIL,
            "id": "user-to-delete",
            "kind": "admin#directory#user",
        }
    )

    DeleteUser.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    # Verify the user was actually removed from the product
    assert product.get_directory_user(PRIMARY_EMAIL) is None


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_delete_user_not_found(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No user seeded — mock returns 404 → GSuiteNotFoundException
    DeleteUser.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == NOT_FOUND_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED


@set_metadata(integration_config=CONFIG_WITHOUT_CREDS, parameters=ACTION_PARAMETERS)
def test_delete_user_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No credentials → auth manager raises before any HTTP call
    DeleteUser.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
