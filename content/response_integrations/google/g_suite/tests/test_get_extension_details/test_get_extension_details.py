from TIPCommon.base.action import ExecutionState

from g_suite.actions import GetExtensionDetails
from g_suite.tests.common import (
    CONFIG,
    DEVICE_DETAILS_DATA,
    EXTENSION_DETAILS_DATA,
    USER_DETAILS_DATA,
)
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

EXTENSION_ID: str = "mclkkofklkfljcocdinagocijmpgbhab"
ACTION_PARAMETERS: dict[str, str | int] = {
    "Extension ID": EXTENSION_ID,
    "Max Requesting Users To Return": 100,
    "Max Requesting Devices To Return": 100,
}

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully returned information about the following extensions in "
    "Google Workspace: Google Input Tools."
)
FAILED_OUTPUT_MESSAGE: str = "No information about the provided extensions were found."


@set_metadata(
    integration_config=CONFIG,
    parameters=ACTION_PARAMETERS,
)
def test_get_extension_details_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_extension_details([EXTENSION_DETAILS_DATA])
    product.add_requesting_users([USER_DETAILS_DATA])
    product.add_requesting_devices([DEVICE_DETAILS_DATA])

    GetExtensionDetails.main()

    assert len(script_session.request_history) >= 5
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=CONFIG,
    parameters=ACTION_PARAMETERS,
)
def test_get_extension_details_failed(
    script_session: ApiSession,
    action_output: MockActionOutput,
) -> None:
    GetExtensionDetails.main()

    assert len(script_session.request_history) >= 3
    assert FAILED_OUTPUT_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED
