from __future__ import annotations

from TIPCommon.base.action import ExecutionState

from g_suite.actions import Ping
from g_suite.tests.common import CONFIG
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully connected to the GSuite instance with the provided connection parameters!"
)

CONFIG_WITHOUT_CREDS: dict = {**CONFIG, "Workload Identity Email": None, "Service Account JSON": None}


@set_metadata(integration_config=CONFIG)
def test_ping_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.set_directory_users([{"primaryEmail": "admin@domain.com"}])

    Ping.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(integration_config=CONFIG_WITHOUT_CREDS)
def test_ping_api_error(
    _script_session: ApiSession,
    _product: Product,
    action_output: MockActionOutput,
) -> None:
    # No valid credentials → auth manager raises an exception before any HTTP call
    Ping.main()

    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
