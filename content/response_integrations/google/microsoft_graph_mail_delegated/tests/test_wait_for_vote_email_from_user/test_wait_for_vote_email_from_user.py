import copy
import datetime
from SiemplifyAction import SiemplifyAction
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput, ActionJsonOutput
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from actions\
    .WaitForVoteEmailResults import WaitForVoteEmailResultsAction
from core.datamodels import (
    MicrosoftGraphEmail,
)
from tests.common import (
    CONFIG_PATH,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
)
from tests.core.session import MsGraphSession
from tests.core.product import (
    MicrosoftGraphMailDelegated,
)
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE = f"Found the reply for users: {DEFAULT_EMAIL.sender}"
ACTION_SUCCESS_JSON = {
    "Responses": [{"recipient": f"{DEFAULT_EMAIL.sender}", "vote": "None"}]
}
SUCCESS_OUTPUT_MESSAGE = ActionOutput(
    output_message=SUCCESS_OUTPUT_MESSAGE,
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=ActionJsonOutput(json_result=ACTION_SUCCESS_JSON),
)

ACTION_INPROGRESS_JSON = {"Responses": []}
ACTION_INPROGRESS_OUTPUT = ActionOutput(
    output_message=(
        'Continuing...waiting for response, searching IN-REPLY-TO "NoReplyID".'
    ),
    result_value=True,
    execution_state=ExecutionState.IN_PROGRESS,
    json_output=ActionJsonOutput(json_result=ACTION_INPROGRESS_JSON),
)

ACTION_FAILED_OUTPUT = ActionOutput(
    output_message=(
        "Failed to execute action. Error: "
        "The provided mail id InvalidMailId was not found."
    ),
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)
SCRIPT_DEADLINE_TIME = datetime.datetime.now() + datetime.timedelta(minutes=10)

EMAIL = copy.deepcopy(DEFAULT_EMAIL)


@set_metadata(
    parameters={
        "Vote Mail Sent From": "Default Mailbox",
        "Mail ID": EMAIL.id,
        "Wait for All Recipients to Reply?": "false",
        "Wait Stage Exclude pattern": "",
        "Folder to Check for Reply": "Inbox",
        "Folder to Check for Sent Mail": "Sent Items",
        "Fetch Response Attachments": "false",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_wait_for_vote_email_from_user_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    siemplify: SiemplifyAction = SiemplifyAction()
    WaitForVoteEmailResultsAction(siemplify).run()

    assert len(script_session.request_history) == 6
    assert action_output.results == SUCCESS_OUTPUT_MESSAGE


@set_metadata(
    parameters={
        "Vote Mail Sent From": "Default Mailbox",
        "Mail ID": "NoReplyID",
        "Wait for All Recipients to Reply?": "true",
        "Wait Stage Exclude pattern": "",
        "Folder to Check for Reply": "Inbox",
        "Folder to Check for Sent Mail": "Sent Items",
        "Fetch Response Attachments": "false",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_wait_for_vote_email_from_user_inprogress(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    email: MicrosoftGraphEmail = EMAIL
    email.id: str = "NoReplyID"
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(email)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    siemplify: SiemplifyAction = SiemplifyAction()
    WaitForVoteEmailResultsAction(siemplify).run()

    assert len(script_session.request_history) == 6
    assert action_output.results == ACTION_INPROGRESS_OUTPUT


@set_metadata(
    parameters={
        "Vote Mail Sent From": "Default Mailbox",
        "Mail ID": "InvalidMailId",
        "Wait for All Recipients to Reply?": "true",
        "Wait Stage Exclude pattern": "",
        "Folder to Check for Reply": "Inbox",
        "Folder to Check for Sent Mail": "Sent Items",
        "Fetch Response Attachments": "false",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_wait_for_vote_email_from_user_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    email: MicrosoftGraphEmail = DEFAULT_EMAIL
    email.id: str = "InvalidMailId"
    ms_graph_mail.add_email(email)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    siemplify: SiemplifyAction = SiemplifyAction()

    WaitForVoteEmailResultsAction(siemplify).run()

    assert len(script_session.request_history) == 4
    assert action_output.results == ACTION_FAILED_OUTPUT
