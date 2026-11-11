from __future__ import annotations

import json

from TIPCommon.base.action import ExecutionState

from g_suite.actions import ListOUOfAccount
from g_suite.tests.common import CONFIG, OU_DETAILS_DATA
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

CUSTOMER_ID: str = "my_customer"

ACTION_PARAMETERS: dict[str, str | int] = {
    "Customer ID": CUSTOMER_ID,
    "Max Organization Units": 50,
}

SUCCESS_OUTPUT_MESSAGE: str = "Successfully fetched organizational units."


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_ou_of_account_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_org_units(OU_DETAILS_DATA)

    ListOUOfAccount.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None
    assert action_output.results.result_value != json.dumps([])


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_ou_of_account_empty(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_org_units([])

    ListOUOfAccount.main()

    assert len(script_session.request_history) > 0
    # ISSUE FINDER: ListOUOfAccount treats an empty result the same as a
    # successful fetch — output_message is still SUCCESS and execution_state
    # is COMPLETED. There is no "no results found" branch in the action.
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value == json.dumps([])
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_list_ou_of_account_api_error(
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
        ListOUOfAccount.main()
        assert _ao.results.execution_state == ExecutionState.FAILED

    _run(script_session, _product, action_output)
