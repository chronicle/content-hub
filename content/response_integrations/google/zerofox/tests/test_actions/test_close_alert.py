from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from TIPCommon.types import SingleJson

from zerofox.actions import CloseAlert
from zerofox.core.constants import CLOSE_ALERT_SCRIPT_NAME
from zerofox.tests import common
from zerofox.tests.core.product import Zerofox
from zerofox.tests.core.session import ZerofoxSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ALERT: SingleJson = common.LIST_ALERTS["alerts"][0]
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully closed alert with ID {ALERT['id']}."
)
FAILED_OUTPUT_MESSAGE: str = (
    f'Error executing action "{CLOSE_ALERT_SCRIPT_NAME}".\nReason: Alert with '
    f"ID {common.INVALID_ALERT_ID} wasn't found in Zerofox."
)

DEFAULT_PARAMETERS: dict[str, str] = {"Alert ID": ALERT["id"]}
FAILED_PARAMETERS: dict[str, str] = {"Alert ID": common.INVALID_ALERT_ID}


@set_metadata(integration_config=common.CONFIG, parameters=DEFAULT_PARAMETERS)
def test_close_alert_success(
    zerofox: Zerofox,
    script_session: ZerofoxSession,
    action_output: MockActionOutput,
) -> None:
    zerofox.cleanup_alerts()
    alert = ALERT.copy()
    zerofox.add_alert(alert)
    CloseAlert.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=SUCCESS_OUTPUT_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )


@set_metadata(integration_config=common.CONFIG, parameters=FAILED_PARAMETERS)
def test_close_alert_failure(
    zerofox: Zerofox,
    script_session: ZerofoxSession,
    action_output: MockActionOutput,
) -> None:
    zerofox.cleanup_alerts()
    alert = ALERT.copy()
    alert["id"] = common.INVALID_ALERT_ID
    zerofox.add_alert(alert)
    CloseAlert.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
