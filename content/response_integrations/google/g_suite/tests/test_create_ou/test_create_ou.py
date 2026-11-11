from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import CreateOU
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CUSTOMER_ID: str = "my_customer"
OU_NAME: str = "TestUnit"
PARENT_PATH: str = "/"

ACTION_PARAMETERS: dict[str, str] = {
    "Customer ID": CUSTOMER_ID,
    "Name": OU_NAME,
    "Description": "A test org unit",
    "Parent OU Path": PARENT_PATH,
}

SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully created organization unit {OU_NAME} for customer id "
    f"            {CUSTOMER_ID} with organization unit "
    f"parent path {PARENT_PATH}"
)


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_create_ou_success(
    script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    CreateOU.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_create_ou_api_error(
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
        CreateOU.main()
        assert _ao.results.execution_state == ExecutionState.FAILED
        assert _ao.results.result_value is False

    _run(script_session, _product, action_output)
