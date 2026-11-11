from TIPCommon.base.action import ExecutionState

from g_suite.actions import RemoveExtension
from g_suite.tests.common import (
    CONFIG,
    OU_DETAILS_DATA,
    ORG_UNIT_NAME,
    REMOVED_POLICY_DATA,
)
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

EXTENSION_ID: str = "mclkkofklkfljcocdinagocijmpgbhab"
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully removed extension “{EXTENSION_ID}” in Organization Unit "
    f"{ORG_UNIT_NAME} using Google Workspace."
)
NOT_FOUND_OUTPUT_MESSAGE: str = f"Organizational Unit '{ORG_UNIT_NAME}' not found."
VALIDATION_FAILED_MESSAGE: str = (
    f"Failed to validate policy deletion for extension '{EXTENSION_ID}'. "
    f"Policy is still directly applied to the OU."
)

ACTION_PARAMETERS: dict[str, str] = {
    "Extension ID": EXTENSION_ID,
    "Organization Unit Name": ORG_UNIT_NAME,
}


@set_metadata(
    integration_config=CONFIG,
    parameters=ACTION_PARAMETERS,
)
def test_remove_extension_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_org_units(OU_DETAILS_DATA)
    product.add_resolved_policies([REMOVED_POLICY_DATA])

    RemoveExtension.main()

    assert len(script_session.request_history) >= 5
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=CONFIG,
    parameters=ACTION_PARAMETERS,
)
def test_remove_extension_ou_not_found(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_org_units([])

    RemoveExtension.main()

    assert len(script_session.request_history) >= 3
    assert NOT_FOUND_OUTPUT_MESSAGE in action_output.results.output_message
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.FAILED
