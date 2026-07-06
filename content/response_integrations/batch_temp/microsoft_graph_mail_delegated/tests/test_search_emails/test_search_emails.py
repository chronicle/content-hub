import copy
import datetime
from SiemplifyAction import SiemplifyAction
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC
from Integrations.MicrosoftGraphMailDelegated.ActionsScripts.SearchEmails import (
    SearchEmailsAction,
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
    "Successfully found emails in the following mailboxes: \ntestuser@test.com: 3"
)
FAILED_OUTPUT_MESSAGE: str = (
    'Failed to execute action. Error: Invalid parameter "Search In Mailbox". '
    "Invalid email address. Wrong value provided: Fail"
)

SCRIPT_DEADLINE_TIME = datetime.datetime.now() + datetime.timedelta(minutes=10)


@set_metadata(
    parameters={
        "Search in Mailbox": "Default Mailbox",
        "Folder Name": "Inbox",
        "Subject Filter": "Some Subject",
        "Sender Filter": "Text",
        "Time Frame (minutes)": "",
        "Select All Fields For Return": "False",
        "Max Emails To Return": "",
        "Only Unread": "False",
        "How many mailboxes to process in a single batch": "",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_search_emails_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    email_1: str = copy.deepcopy(DEFAULT_EMAIL)
    email_2: str = copy.deepcopy(DEFAULT_EMAIL)
    email_3: str = copy.deepcopy(DEFAULT_EMAIL)
    email_1.id = "1"
    email_2.id = "2"
    email_3.id = "3"
    email_1.raw_data["id"] = "1"
    email_2.raw_data["id"] = "2"
    email_3.raw_data["id"] = "3"
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(email_1)
    ms_graph_mail.add_email(email_2)
    ms_graph_mail.add_email(email_3)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    siemplify = SiemplifyAction()
    SearchEmailsAction(siemplify).run()

    assert len(script_session.request_history) == 4
    assert action_output.results.output_message == SUCCESS_OUTPUT_MESSAGE
    assert action_output.results.result_value is True
    assert action_output.results.execution_state == ExecutionState.COMPLETED
    assert action_output.results.json_output.json_result[0]["Emails"][0]["id"] == "1"
    assert action_output.results.json_output.json_result[0]["Emails"][1]["id"] == "2"
    assert action_output.results.json_output.json_result[0]["Emails"][2]["id"] == "3"


@set_metadata(
    parameters={
        "Search in Mailbox": "Fail",
        "Folder Name": "Junk",
        "Subject Filter": "Some Subject",
        "Sender Filter": "FailIt",
        "Time Frame (minutes)": "",
        "Select All Fields For Return": "False",
        "Max Emails To Return": "",
        "Only Unread": "False",
    },
    integration_config_file_path=CONFIG_PATH,
    input_context={
        "execution_deadline_unix_time_ms": int(
            SCRIPT_DEADLINE_TIME.timestamp() * NUM_OF_MILLI_IN_SEC
        )
    },
)
def test_search_emails_failure(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    siemplify = SiemplifyAction()
    SearchEmailsAction(siemplify).run()

    assert len(script_session.request_history) == 0
    assert action_output.results == ActionOutput(
        output_message=FAILED_OUTPUT_MESSAGE,
        result_value=False,
        execution_state=ExecutionState.FAILED,
        json_output=None,
    )
