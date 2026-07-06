from __future__ import annotations

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput

from Integrations.MicrosoftGraphMailDelegated.ActionsScripts.MarkEmailAsJunk import (
    MarkEmailAsJunk,
)
from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG_PATH,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
)
from Tests.integrations.MicrosoftGraphMailDelegated.conftest import MsGraphSession
from Tests.integrations.MicrosoftGraphMailDelegated.core.product import (
    MicrosoftGraphMailDelegated,
)
from Tests.mocks.platform.script_output import MockActionOutput
from Tests.mocks.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE: str = "Successfully marked the email as junk.\n\n"
FAILED_OUTPUT_MESSAGE: str = (
    "Error executing action \"MicrosoftGraphMailDelegated - Mark Email as Junk\"."
    "\nReason: Failed to find any emails based on provided parameters!"
)


@set_metadata(
    parameters={
        "Search In Mailbox": "Default Mailbox",
        "Folder Name": "Inbox",
        "Mail IDs": DEFAULT_EMAIL.id,
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_mark_email_as_junk_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    DEFAULT_EMAIL.moveToJunk = False
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    MarkEmailAsJunk().run()

    assert DEFAULT_EMAIL.moveToJunk is True
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
        "Folder Name": "Inbox",
        "Mail IDs": "InvalidMailId",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_mark_email_as_junk_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    DEFAULT_EMAIL.moveToJunk = False
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    MarkEmailAsJunk().run()

    assert DEFAULT_EMAIL.moveToJunk is False
    assert len(script_session.request_history) == 4
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
