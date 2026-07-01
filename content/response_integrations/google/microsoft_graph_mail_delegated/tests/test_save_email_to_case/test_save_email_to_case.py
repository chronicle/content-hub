from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from actions.SaveEmailToCase import (
    SaveEmailToCase,
)
from tests.common import (
    CONFIG_PATH,
    DEFAULT_ATTACHMENT,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
)
from tests.core.product import (
    MicrosoftGraphMailDelegated,
)
from tests.core.session import MsGraphSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully saved the following attachments\n{DEFAULT_ATTACHMENT.name}\n\n"
)
FAILED_OUTPUT_MESSAGE: str = (
    "Error executing action \"MicrosoftGraphMailDelegated - Save Email to Case\"."
    "\nReason: An error occurred: Id is malformed."
)


@set_metadata(
    parameters={
        "Search In Mailbox": "Default Mailbox",
        "Folder Name": "Inbox",
        "Mail ID": DEFAULT_EMAIL.id,
        "Save Only Email Attachments": "true",
        "Base64 Encode": "false",
        "Save Email to the Case Wall": "true",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_save_email_to_case_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_attachment(DEFAULT_ATTACHMENT)

    SaveEmailToCase().run()

    assert len(script_session.request_history) == 7
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Search In Mailbox": "Default Mailbox",
        "Folder Name": "Inbox",
        "Mail ID": "InvalidMailId",
        "Save Only Email Attachments": "true",
        "Base64 Encode": "false",
        "Save Email to the Case Wall": "true",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_save_email_to_case_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_attachment(DEFAULT_ATTACHMENT)

    SaveEmailToCase().run()

    assert len(script_session.request_history) == 4
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
