import uuid

import pytest
from TIPCommon.base.action import ExecutionState
from actions.AddAlertComment import (
    AddAlertComment,
)
from tests.common import CONFIG_PATH
from tests.core.session import (
    MicrosoftGraphSecuritySession,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


COMMENT: str = "Comment"
ALERT_ID: str = str(uuid.uuid4())
SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully added comment to the alert {ALERT_ID} in Microsoft Graph"
)


@pytest.mark.usefixtures("script_session")
class TestHappyPath:

    @set_metadata(
        parameters={"Alert ID": ALERT_ID, "Comment":COMMENT},
        integration_config_file_path=CONFIG_PATH,
    )
    def test_default_case(
        self,
        script_session: MicrosoftGraphSecuritySession,
        action_output: MockActionOutput,
    ) -> None:
        AddAlertComment().run()

        assert len(script_session.request_history) == 2

        assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
