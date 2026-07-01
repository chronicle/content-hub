from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from actions.SendThreadReply import (
    SendThreadReply,
)
from tests.common import (
    CONFIG_PATH,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
)
from tests.core.product import (
    MicrosoftGraphMailDelegated,
)
from tests.conftest import MsGraphSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = (
    f"Successfully sent reply to the mail with ID {DEFAULT_EMAIL.id}"
)
FAILED_OUTPUT_MESSAGE: str = (
    'Error executing action "MicrosoftGraphMailDelegated - Send Thread Reply".\n'
    "Reason: The provided mail ID InvalidMailId was not found."
)


@set_metadata(
    parameters={
        "Send From": "Default Mailbox",
        "Mail ID": DEFAULT_EMAIL.id,
        "Folder Name": "Inbox",
        "Attachments Paths": "",
        "Reply All": "False",
        "Mail Content": "Hello World",
        "Reply-To": "",
        "Attachment Location": "GCP Bucket",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_send_thread_reply_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    SendThreadReply().run()

    assert len(script_session.request_history) == 8

    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Send From": "Default Mailbox",
        "Mail ID": "InvalidMailId",
        "Folder Name": "Inbox",
        "Attachments Paths": "",
        "Reply All": "False",
        "Mail Content": "Hello World",
        "Reply-To": "",
        "Attachment Location": "GCP Bucket",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_send_thread_reply_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    SendThreadReply().run()

    assert len(script_session.request_history) == 4
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
