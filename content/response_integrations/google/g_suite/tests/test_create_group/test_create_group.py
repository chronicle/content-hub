from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import CreateGroup
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

GROUP_EMAIL: str = "mygroup@domain.com"
GROUP_NAME: str = "My Group"

ACTION_PARAMETERS: dict[str, str] = {
    "Email Address": GROUP_EMAIL,
    "Name": GROUP_NAME,
    "Description": "Test group",
}

SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully created group with email address {GROUP_EMAIL}"
)

CONFIG_WITHOUT_CREDS: dict = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}


@set_metadata(integration_config=CONFIG, parameters=ACTION_PARAMETERS)
def test_create_group_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    CreateGroup.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output is not None
    # Verify the group was registered in the product
    assert product.get_group(GROUP_EMAIL) is not None


@set_metadata(integration_config=CONFIG_WITHOUT_CREDS, parameters=ACTION_PARAMETERS)
def test_create_group_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No credentials → auth manager raises before any HTTP call
    CreateGroup.main()

    assert action_output.results.execution_state == ExecutionState.FAILED
    assert action_output.results.result_value is False
