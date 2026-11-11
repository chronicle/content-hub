from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from okta.actions import ping
from okta.tests.common import CONFIG_PATH
from okta.tests.core.session import (
    Session,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


@set_metadata(integration_config_file_path=CONFIG_PATH)
def test_ping(
    script_session: Session,
    action_output: MockActionOutput,
) -> None:
    ping.main()

    assert len(script_session.request_history) == 1
    assert action_output.results == ActionOutput(
        output_message="Connection Established Successfully",
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
        debug_output="",
    )
