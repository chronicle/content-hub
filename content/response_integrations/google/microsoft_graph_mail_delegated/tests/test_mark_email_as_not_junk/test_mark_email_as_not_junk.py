from __future__ import annotations

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from actions.MarkEmailAsNotJunk import (
    MarkEmailAsNotJunk,
)
from tests.common import (
    CONFIG_PATH,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
)
from tests.conftest import MsGraphSession
from tests.core.product import (
    MicrosoftGraphMailDelegated,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE: str = "Successfully marked the email as not junk.\n\n"
FAILED_OUTPUT_MESSAGE: str = (
    "Error executing action \"MicrosoftGraphMailDelegated - Mark Email as Not Junk\"."
    "\nReason: Failed to find any emails based on provided parameters!"
)

@set_metadata(
    parameters={
        "Search In Mailbox": "Default Mailbox",
        "Folder Name": "Junk",
        "Mail IDs": DEFAULT_EMAIL.id,
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_mark_email_as_not_junk_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    DEFAULT_EMAIL.moveToInbox = False
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_email(DEFAULT_EMAIL)

    MarkEmailAsNotJunk().run()

    assert DEFAULT_EMAIL.moveToInbox is True
    assert len(script_session.request_history) == 5
    assert action_output.results == ActionOutput(
        output_message=SUCCESS_OUTPUT_MESSAGE,
        result_value=True,
        execution_state=ExecutionState.COMPLETED,
        json_output=None,
    )

@set_metadata(
    parameters={
        "Search In Mailbox": "Default Mailbox",
        "Folder Name": "Junk",
        "Mail IDs": "InvalidMailId",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_mark_email_as_not_junk_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    DEFAULT_EMAIL.moveToInbox = False
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_email(DEFAULT_EMAIL)

    MarkEmailAsNotJunk().run()

    assert DEFAULT_EMAIL.moveToInbox is False
    assert len(script_session.request_history) == 4
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
