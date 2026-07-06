import datetime
from SiemplifyAction import SiemplifyAction
from TIPCommon.base.action import ExecutionState
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from TIPCommon.base.data_models import ActionJsonOutput, ActionOutput
from Integrations.MicrosoftGraphMailDelegated.ActionsScripts.MoveEmailToFolder import (
    MoveEmailAction,
)
from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG_PATH,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.product import (
    MicrosoftGraphMailDelegated,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.session import MsGraphSession
from Tests.mocks.platform.script_output import MockActionOutput
from Tests.mocks.set_meta import set_metadata


SUCCESS_OUTPUT_MESSAGE: str = (
    "Successfully moved emails in the following mailboxes: \ntestuser@test.com: 1"
)
INPROGRESS_OUTPUT_MESSAGE: str = (
    "Successfully processed mailboxes: 1, Pending mailboxes: 1. Continuing..."
)
FAILURE_OUTPUT_MESSAGE: str = (
    "The action didn't find any emails based on the specified search criteria"
)

SCRIPT_DEADLINE_TIME = datetime.datetime.now() + datetime.timedelta(minutes=10)


@set_metadata(
    parameters={
        "Move In Mailbox": "Default Mailbox",
        "Source Folder Name": "Junk Email",
        "Destination Folder Name": "Inbox",
        "Mail IDs": DEFAULT_EMAIL.id,
        "Subject Filter": "Some Subject",
        "Sender Filter": "Text",
        "Time Frame (minutes)": "",
        "Only Unread": "False",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_move_email_to_folder_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    siemplify = SiemplifyAction()
    MoveEmailAction(siemplify).run()

    assert len(script_session.request_history) == 8
    assert action_output.results.result_value is True
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.execution_state == ExecutionState.COMPLETED


@set_metadata(
    parameters={
        "Move In Mailbox": "Default Mailbox, abcd@gmail.com",
        "Source Folder Name": "Junk Email",
        "Destination Folder Name": "Inbox",
        "Mail IDs": DEFAULT_EMAIL.id,
        "Subject Filter": "Some Subject",
        "Sender Filter": "Text",
        "Time Frame (minutes)": "",
        "Only Unread": "False",
        "How many mailboxes to process in a single batch": "1",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_move_email_to_folder_inprogress(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_email(DEFAULT_EMAIL)

    siemplify = SiemplifyAction()
    MoveEmailAction(siemplify).run()

    assert len(script_session.request_history) == 9
    assert isinstance(action_output.results.result_value, str) is True
    assert action_output.results.output_message == INPROGRESS_OUTPUT_MESSAGE
    assert action_output.results.execution_state == ExecutionState.IN_PROGRESS


@set_metadata(
    parameters={
        "Move In Mailbox": "Default Mailbox",
        "Source Folder Name": "Junk Email",
        "Destination Folder Name": "Inbox",
        "Mail IDs": "InvalidMailId",
        "Subject Filter": "Some Subject",
        "Sender Filter": "Text",
        "Time Frame (minutes)": "",
        "Only Unread": "False",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_move_email_to_folder_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    siemplify = SiemplifyAction()
    MoveEmailAction(siemplify).run()

    assert len(script_session.request_history) == 5
    assert action_output.results == ActionOutput(
        output_message=FAILURE_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=ActionJsonOutput(json_result=[]),
    )
