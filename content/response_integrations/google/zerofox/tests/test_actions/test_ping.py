from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from zerofox.actions import Ping
from zerofox.core.constants import INTEGRATION_NAME
from zerofox.tests import common
from zerofox.tests.core.product import Zerofox
from zerofox.tests.core.session import ZerofoxSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


PING_SUCCESS_MESSAGE: str = (
    f"Successfully connected to the {INTEGRATION_NAME} "
    "server with the provided connection parameters!"
)
FAILED_OUTPUT_MESSAGE: str = (
    "Failed to connect to the Zerofox server!\nReason: Authentication failed: "
    "Invalid API token."
)
ALERT = common.LIST_ALERTS["alerts"][0]

@set_metadata(integration_config=common.CONFIG)
def test_ping_success(
    zerofox: Zerofox,
    script_session: ZerofoxSession,
    action_output: MockActionOutput,
) -> None:
    zerofox.cleanup_alerts()
    alert = ALERT.copy()
    zerofox.add_alert(alert)
    Ping.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=PING_SUCCESS_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )


@set_metadata(integration_config=common.CONFIG)
def test_ping_failure(
    zerofox: Zerofox,
    script_session: ZerofoxSession,
    action_output: MockActionOutput,
) -> None:
    zerofox.cleanup_alerts()
    alert = ALERT.copy()
    alert["id"] = common.INVALID_ALERT_ID
    zerofox.add_alert(alert)
    Ping.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
