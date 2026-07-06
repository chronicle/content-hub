from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from Integrations.MicrosoftGraphMailDelegated.ActionsScripts\
    .ExtractDataFromAttachedEML import ExtractEmlData
from Integrations.MicrosoftGraphMailDelegated.Managers.datamodels import (
    MicrosoftGraphEmail,
)
from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG_PATH,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
    DEFAULT_ATTACHMENT,
)
from Tests.integrations.MicrosoftGraphMailDelegated.conftest import MsGraphSession
from Tests.integrations.MicrosoftGraphMailDelegated.core.product import (
    MicrosoftGraphMailDelegated,
)
from Tests.mocks.platform.script_output import MockActionOutput
from Tests.mocks.set_meta import set_metadata


JSON_OUTPUT = ActionJsonOutput(
    json_result=[
        {
            "type": "EML",
            "subject": "",
            "from": "",
            "to": "",
            "date": "",
            "text": "some_text",
            "html": "some_text",
            "regex": {},
            "regex_from_text_part": {},
            "id": (
                "AAMkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMDI4ZTZlNQBGAAAAAADLc0XF-C"
                "8kRJTduC5WOJE-BwDby9ZjVdTJTJRS8jxrcA_oAARzV4LIAADby9ZjVdTJTJRS8jxrcA_o"
                "AAToqGwkAAABEgAQAB0ESZTNPlNHpKAXYEOIFCU="
            ),
            "name": "test",
        }
    ]
)
SUCCESS_OUTPUT_MESSAGE: str = (
    'Extracted data from "1" attached email files. \n\nFiles:\n"test"'
)
FAILED_OUTPUT_MESSAGE: str = (
    'Error executing action "MicrosoftGraphMailDelegated - Extract Data from '
    'Attached EML".\nReason: Failed to find any emails using the provided criteria!'
)

ACTION_SUCCESS_OUTPUT = ActionOutput(
    output_message=SUCCESS_OUTPUT_MESSAGE,
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=JSON_OUTPUT,
)

ACTION_FAILURE_OUTPUT = ActionOutput(
    output_message=FAILED_OUTPUT_MESSAGE,
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)


@set_metadata(
    parameters={
        "Search In Mailbox": "Default Mailbox",
        "Folder Name": "Inbox",
        "Mail IDs": DEFAULT_EMAIL.id,
        "Regex Map JSON": "{}",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_extract_data_from_attached_eml_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    email: MicrosoftGraphEmail = DEFAULT_EMAIL
    email.has_attachments: bool = True
    ms_graph_mail.add_email(email)
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_attachment(DEFAULT_ATTACHMENT)
    ExtractEmlData().run()

    assert len(script_session.request_history) == 6
    assert action_output.results == ACTION_SUCCESS_OUTPUT


@set_metadata(
    parameters={
        "Search In Mailbox": "Default Mailbox",
        "Folder Name": "Inbox",
        "Mail IDs": "InvalidMailId",
        "Regex Map JSON": "{}",
    },
    integration_config_file_path=CONFIG_PATH,
)
def test_extract_data_from_attached_eml_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    email: MicrosoftGraphEmail = DEFAULT_EMAIL
    email.has_attachments: bool = True
    ms_graph_mail.add_email(email)
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_attachment(DEFAULT_ATTACHMENT)
    ExtractEmlData().run()

    assert len(script_session.request_history) == 4
    assert action_output.results == ACTION_FAILURE_OUTPUT
