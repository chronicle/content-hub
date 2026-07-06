from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from Integrations.MicrosoftGraphMailDelegated.ActionsScripts.SendEmailHTML import (
    SendEmailHTML,
)

from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG_PATH,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
    FAILED_USER_JSON,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.product import (
    MicrosoftGraphMailDelegated,
)

from Tests.integrations.MicrosoftGraphMailDelegated.core.session import MsGraphSession
from Tests.mocks.platform.script_output import MockActionOutput
from Tests.mocks.set_meta import set_metadata

SUCCESS_OUTPUT_MESSAGE: str = "The email was sent successfully."
FAILED_OUTPUT_MESSAGE: str = (
    'Error executing action "MicrosoftGraphMailDelegated - Send Email HTML".\nReason: '
    'The provided mailbox "invalid@mailbox.com" was not found.'
)


@set_metadata(
    parameters={
        "Send From": "Default Mailbox",
        "Subject": "Hello",
        "Send to": "KBC@example.com",
        "CC": "Ht@gmail.com,Nit@example.com,ai@expmple.in",
        "BCC": "Ama@gmail.com",
        "Attachments Paths": "",
        "Email HTML Template": (
            "<html><body><div>\r\n<div>Testing </div></div>\r\n</body></html>"
        ),
        "Reply-To Recipients": "",
        "Attachment Location": "GCP Bucket",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_send_email_html_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    SendEmailHTML().run()

    assert len(script_session.request_history) == 6
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Send From": "invalid@mailbox.com",
        "Subject": "Hello",
        "Send to": "KBC@example.com",
        "CC": "Ht@gmail.com,Nit@example.com,ai@expmple.in",
        "BCC": "Ama@gmail.com",
        "Attachments Paths": "",
        "Email HTML Template": (
            "<html><body><div>\r\n<div>Testing </div></div>\r\n</body></html>"
        ),
        "Reply-To Recipients": "",
        "Attachment Location": "GCP Bucket",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_send_email_html_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(FAILED_USER_JSON)

    SendEmailHTML().run()

    assert len(script_session.request_history) == 2
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
