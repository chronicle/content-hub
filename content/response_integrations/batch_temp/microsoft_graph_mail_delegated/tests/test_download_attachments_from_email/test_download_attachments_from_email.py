import datetime

from SiemplifyAction import SiemplifyAction
from TIPCommon.base.action import ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.base.data_models import ActionOutput, ActionJsonOutput
from Integrations.MicrosoftGraphMailDelegated.ActionsScripts import (
    DownloadAttachmentsFromEmail,
)
from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG_PATH,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
    DEFAULT_ATTACHMENT,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.product import (
    MicrosoftGraphMailDelegated,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.session import MsGraphSession
from Tests.mocks.platform.script_output import MockActionOutput
from Tests.mocks.set_meta import set_metadata


DOWNLOAD_PATH = "/tmp/test"
success_parameters = {
    "Search In Mailbox": "Default Mailbox",
    "Folder Name": "Inbox",
    "Download Destination": "Local File System",
    "Download Path": DOWNLOAD_PATH,
    "Mail IDs": DEFAULT_EMAIL.id,
    "Subject Filter": "The",
    "Sender Filter": "Text",
    "Download Attachments from EML": "",
    "Download Attachments to unique path?": "False",
    "How many mailboxes to process in a single batch": "1",
}

JSON_OUTPUT = ActionJsonOutput(
    json_result=[
        {"attachment_name": "test.eml", "downloaded_path": "/tmp/test/test.eml"}
    ]
)
SUCCESS_OUTPUT_MESSAGE = (
    "Successfully downloaded attachments found in emails in the following "
    "mailboxes: \ntestuser@test.com\n\nDownloaded 1 attachments."
    f"\nContaining Directory: {DOWNLOAD_PATH}\n"
    f"\nFiles:\n{JSON_OUTPUT.json_result[0]['attachment_name']}: "
    f"{JSON_OUTPUT.json_result[0]['downloaded_path']}"
)
INPROGRESS_OUTPUT_MESSAGE = "Mailboxes processed: 1. Continuing..."
FAILURE_OUTPUT_MESSAGE = "Failed to find any emails using the provided criteria!"

ACTION_SUCCESS_OUTPUT = ActionOutput(
    output_message=SUCCESS_OUTPUT_MESSAGE,
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=JSON_OUTPUT,
)
ACTION_FAILURE_OUTPUT = ActionOutput(
    output_message=FAILURE_OUTPUT_MESSAGE,
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=ActionJsonOutput(json_result=[]),
)
SCRIPT_DEADLINE_TIME = datetime.datetime.now() + datetime.timedelta(minutes=10)


@set_metadata(
    parameters=success_parameters,
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_download_attachments_from_email_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_attachment(DEFAULT_ATTACHMENT)

    siemplify: SiemplifyAction = SiemplifyAction()

    DownloadAttachmentsFromEmail.DownloadAttachmentsFromEmailAction(siemplify).run()

    assert len(script_session.request_history) == 6
    assert action_output.results == ACTION_SUCCESS_OUTPUT


@set_metadata(
    parameters={
        "Search In Mailbox": "Default Mailbox, abcd@gmail.com",
        "Folder Name": "Junk Email",
        "Download Destination": "Local File System",
        "Download Path": "/tmp/test",
        "Mail IDs": DEFAULT_EMAIL.id,
        "Subject Filter": "Some Subject",
        "Sender Filter": "Text",
        "Download Attachments from EML": "",
        "Download Attachments to unique path?": "False",
        "How many mailboxes to process in a single batch": "1",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_download_attachments_from_email_inprogress(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_attachment(DEFAULT_ATTACHMENT)

    siemplify: SiemplifyAction = SiemplifyAction()
    DownloadAttachmentsFromEmail.DownloadAttachmentsFromEmailAction(siemplify).run()

    assert len(script_session.request_history) == 7
    assert isinstance(action_output.results.result_value, str)
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS
    assert action_output.results.output_message == INPROGRESS_OUTPUT_MESSAGE


@set_metadata(
    parameters={
        "Search In Mailbox": "Default Mailbox",
        "Folder Name": "Inbox",
        "Download Destination": "Local File System",
        "Download Path": "./",
        "Mail IDs": "InvalidMailId",
        "Subject Filter": "",
        "Sender Filter": "",
        "Download Attachments from EML": "false",
        "Download Attachments to unique path?": "false",
        "How many mailboxes to process in a single batch": "1",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_download_attachments_from_email_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    siemplify: SiemplifyAction = SiemplifyAction()
    DownloadAttachmentsFromEmail.DownloadAttachmentsFromEmailAction(siemplify).run()

    assert len(script_session.request_history) == 4
    assert action_output.results == ACTION_FAILURE_OUTPUT
