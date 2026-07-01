from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from actions.SendVoteEmail import (
    SendVoteEmail,
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
from tests.core.session import MsGraphSession
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = "The email was sent successfully."
FAILED_OUTPUT_MESSAGE: str = (
    'Error executing action "MicrosoftGraphMailDelegated - Send Vote Email".\nReason: '
    'The provided mailbox "invalid@mailbox.com" was not found.'
)


@set_metadata(
    parameters={
        "Send From": "Default Mailbox",
        "Send to": "abc@def.com",
        "Subject": "Some subject",
        "CC": "Hello",
        "BCC": "Inbox",
        "Attachments Paths": "",
        "Email HTML Template": "False",
        "Structure of voting options": "Hello World",
        "Reply-To Recipients": "",
        "Attachment Location": "GCP Bucket",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_send_vote_email_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    SendVoteEmail().run()

    assert len(script_session.request_history) == 6
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Send From": "invalid@mailbox.com",
        "Send to": "abc@def.com",
        "Subject": "Some subject",
        "CC": "Hello",
        "BCC": "Inbox",
        "Attachments Paths": "",
        "Email HTML Template": "False",
        "Structure of voting options": "Hello World",
        "Reply-To Recipients": "",
        "Attachment Location": "GCP Bucket",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_send_vote_email_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    SendVoteEmail().run()

    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
