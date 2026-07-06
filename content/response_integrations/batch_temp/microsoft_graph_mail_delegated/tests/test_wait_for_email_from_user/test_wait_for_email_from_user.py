import copy
import datetime

from SiemplifyAction import SiemplifyAction
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput, ActionJsonOutput
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from Integrations.MicrosoftGraphMailDelegated.ActionsScripts\
    .WaitForEmailFromUser import WaitForMailFromUserAction
from Integrations.MicrosoftGraphMailDelegated.Managers.datamodels import (
    MicrosoftGraphEmail,
)
from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG_PATH,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.session import MsGraphSession
from Tests.integrations.MicrosoftGraphMailDelegated.core.product import (
    MicrosoftGraphMailDelegated,
)
from Tests.mocks.platform.script_output import MockActionOutput
from Tests.mocks.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE = f"The action found the reply for users: {DEFAULT_EMAIL.sender}"
ACTION_SUCCESS_JSON = {
    "Responses": [
        {
            "recipient": f"{DEFAULT_EMAIL.sender}",
            "content": {
                "id": (
                    "AAMkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMDI4ZTZlNQBGAAAAAADLc"
                    "0XF-C8kRJTduC5WOJE-BwDby9ZjVdTJTJRS8jxrcA_oAALg_Vq3AADby9ZjVdT"
                    "JTJRS8jxrcA_oAAP1qhPJAAA="
                ),
                "internetMessageId": (
                    "<DB9PR05MB79627ADBED8E2BBAE6B596FBBE9EA@DB9PR05MB7962."
                    "eurprd05.prod.outlook.com>"
                ),
                "sender": "abc@example.com",
                "subject": "Testing Mail wait for user to reply",
                "toRecipients": "abc@example.com",
                "receivedDateTime": "2023-12-28T10:15:35Z"
            },
        }
    ],
}
ACTION_SUCCESS_OUTPUT = ActionOutput(
    output_message=SUCCESS_OUTPUT_MESSAGE,
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=ActionJsonOutput(json_result=ACTION_SUCCESS_JSON),
)

INPROGRESS_OUTPUT_JSON = {"Responses": []}
ACTION_INPROGRESS_OUTPUT = ActionOutput(
    output_message=(
        'Continuing...waiting for response, searching IN-REPLY-TO "NoReplyID".'
    ),
    result_value=True,
    execution_state=ExecutionState.IN_PROGRESS,
    json_output=ActionJsonOutput(json_result=INPROGRESS_OUTPUT_JSON),
)
ACTION_FAILED_OUTPUT = ActionOutput(
    output_message=(
        "Failed to execute action. Error: An error occurred: Id is malformed."
    ),
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)

SCRIPT_DEADLINE_TIME = datetime.datetime.now() + datetime.timedelta(minutes=10)

EMAIL = copy.deepcopy(DEFAULT_EMAIL)


@set_metadata(
    parameters={
        "Mail ID": EMAIL.id,
        "Wait for All Recipients to Reply?": "false",
        "Wait Stage Exclude pattern": "",
        "Folder to Check for Reply": "Inbox",
        "Fetch Response Attachments": "false",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_wait_for_mail_from_user_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_email(EMAIL)

    siemplify: SiemplifyAction = SiemplifyAction()

    WaitForMailFromUserAction(siemplify).run()

    assert len(script_session.request_history) == 5
    assert action_output.results == ACTION_SUCCESS_OUTPUT


@set_metadata(
    parameters={
        "Mail ID": "NoReplyID",
        "Wait for All Recipients to Reply?": "true",
        "Wait Stage Exclude pattern": "",
        "Folder to Check for Reply": "Inbox",
        "Fetch Response Attachments": "false",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_wait_for_mail_from_user_inprogress(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    email: MicrosoftGraphEmail = EMAIL
    email.id: str = "NoReplyID"
    ms_graph_mail.add_email(email)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    siemplify: SiemplifyAction = SiemplifyAction()
    WaitForMailFromUserAction(siemplify).run()

    assert len(script_session.request_history) == 5
    assert action_output.results == ACTION_INPROGRESS_OUTPUT


@set_metadata(
    parameters={
        "Mail ID": "InvalidMailId",
        "Wait for All Recipients to Reply?": "false",
        "Wait Stage Exclude pattern": "",
        "Folder to Check for Reply": "",
        "Fetch Response Attachments": "false",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_wait_for_mail_from_user_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    email: MicrosoftGraphEmail = EMAIL
    email.id: str = "InvalidMailId"
    ms_graph_mail.add_email(email)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    siemplify: SiemplifyAction = SiemplifyAction()

    WaitForMailFromUserAction(siemplify).run()

    assert len(script_session.request_history) == 4
    assert action_output.results == ACTION_FAILED_OUTPUT
