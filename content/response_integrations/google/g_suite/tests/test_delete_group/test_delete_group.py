from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import DeleteGroup
from g_suite.core.consts import INTEGRATION_NAME
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

GROUP_EMAIL: str = "todelete@domain.com"

ACTION_PARAMETERS: dict[str, str] = {
    "Group Email Address": GROUP_EMAIL,
}

SUCCESS_OUTPUT_MESSAGE: str = f"{INTEGRATION_NAME} group deleted."
NOT_FOUND_OUTPUT_MESSAGE: str = (
    f"Action was not able to find {INTEGRATION_NAME} group for deletion."
)

CONFIG_WITHOUT_CREDS: dict = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_delete_group_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_group(GROUP_EMAIL, {"email": GROUP_EMAIL, "id": "grp-id-1"})

    DeleteGroup.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert product.get_group(GROUP_EMAIL) is None


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_delete_group_not_found(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No group seeded — mock returns 404 → caught by inner except → not-found message
    DeleteGroup.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == NOT_FOUND_OUTPUT_MESSAGE
    # ISSUE FINDER: DeleteGroup sets result_value=False but execution_state=COMPLETED
    # when the group is not found. The outer try only fails on auth errors.
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG_WITHOUT_CREDS, parameters=ACTION_PARAMETERS)
def test_delete_group_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No credentials → auth manager raises before any HTTP call
    DeleteGroup.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
