import datetime

from TIPCommon.base.action import EntityTypesEnum, ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.types import Entity

from g_suite.actions import GetHostBrowserDetails
from g_suite.tests.common import CONFIG, HOST_BROWSER_DETAILS_DATA
from g_suite.tests.core.product import Product
from g_suite.tests.core.session import ApiSession
from integration_testing.common import create_entity
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully returned browsers related to the following hostnames in Google "
    "Workspace: hostname1.com."
)
FAILED_OUTPUT_MESSAGE: str = "No browsers were associated with provided hostnames."

HOSTNAME_ENTITY: Entity = create_entity("hostname1.com", EntityTypesEnum.HOST_NAME)
SCRIPT_DEADLINE_TIME: datetime.datetime = datetime.datetime.now() + datetime.timedelta(
    minutes=10
)
DEADLINE_MS = int(SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC)


@set_metadata(
    integration_config=CONFIG,
    entities=[HOSTNAME_ENTITY],
    input_context={"execution_deadline_unix_time_ms": DEADLINE_MS},
)
def test_get_host_browser_details_success(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_host_browser_details([HOST_BROWSER_DETAILS_DATA])
    GetHostBrowserDetails.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    integration_config=CONFIG,
    entities=[HOSTNAME_ENTITY],
    input_context={"execution_deadline_unix_time_ms": DEADLINE_MS},
)
def test_get_host_browser_details_failed(
    script_session: ApiSession,
    product: Product,
    action_output: MockActionOutput,
) -> None:
    product.add_host_browser_details([])
    GetHostBrowserDetails.main()

    assert len(script_session.request_history) > 0
    assert action_output.results.output_message == FAILED_OUTPUT_MESSAGE
    assert action_output.results.result_value is False
    assert action_output.results.execution_state == ExecutionState.COMPLETED
