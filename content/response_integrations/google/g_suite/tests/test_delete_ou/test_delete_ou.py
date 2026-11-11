from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import DeleteOU
from g_suite.core.consts import DELETE_OU_SCRIPT_NAME
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CUSTOMER_ID: str = "my_customer"
OU_PATH: str = "/TestUnit"

ACTION_PARAMETERS: dict[str, str] = {
    "Customer ID": CUSTOMER_ID,
    "OU Path": OU_PATH,
}

SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully deleted organization unit for customer id"
    f"{CUSTOMER_ID} with organization unit path {OU_PATH}"
)
INVALID_CUSTOMER_OUTPUT_MESSAGE: str = (
    f"Error executing action {DELETE_OU_SCRIPT_NAME}. Reason: Customer ID is invalid"
)


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_delete_ou_success(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # The mock delete_ou always returns 200 regardless of OU existence
    DeleteOU.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_delete_ou_api_error(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    bad_config = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}

    @set_metadata(integration_config=bad_config, parameters=ACTION_PARAMETERS)
    def _run(
        _ss: ApiSession,
        __p: Product,
        _ao: MockActionOutput,
    ) -> None:
        DeleteOU.main()
        assert _ao.results.execution_state == ExecutionState.FAILED
        assert _ao.results.result_value is False

    _run(script_session, _product, action_output)
