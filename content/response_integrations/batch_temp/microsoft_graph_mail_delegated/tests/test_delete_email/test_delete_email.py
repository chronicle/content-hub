import datetime
import json

from SiemplifyAction import SiemplifyAction
from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput
from TIPCommon.consts import NUM_OF_MILLI_IN_SEC

from Integrations.MicrosoftGraphMailDelegated.ActionsScripts.DeleteEmail import (
    DeleteEmailAction,
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
    "Successfully deleted emails in the following mailboxes: \ntestuser@test.com: 1"
)
INPROGRESS_OUTPUT_MESSAGE: str = (
    "Successfully processed mailboxes: 1, Pending mailboxes: 1. Continuing..."
)
FAILURE_OUTPUT_MESSAGE: str = (
    "The action didn't find any emails based on the specified search criteria"
)

ACTION_SUCCESS_OUTPUT = ActionOutput(
    output_message=SUCCESS_OUTPUT_MESSAGE,
    result_value=True,
    execution_state=ExecutionState.COMPLETED,
    json_output=None,
)

ACTION_INPROGRESS_RESULT_VALUE = {
    "processed_mailboxes": {
        "testuser@test.com": [
            (
                "AAMkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMDI4ZTZlNQBGAAAAAADLc0XF-C"
                "8kRJTduC5WOJE-BwDby9ZjVdTJTJRS8jxrcA_oAALg_Vq3AADby9ZjVdTJTJRS8jxrcA_o"
                "AAP1qhPJAAA="
            )
        ]
    },
    "pending_mailboxes": ["testuser@test.com"],
    "failed_mailboxes": [],
    "failed_folder_mailboxes": [],
    "all_deleted_emails": [
        {
            "@odata.context": (
                "https://graph.microsoft.com/v1.0/$metadata#users('abc%40siemplif"
                "ycyarx.onmicrosoft.com')/mailFolders('AQMkADU0MDJjNjJkLTc3ADMwLTRjO"
                "TMtOGYzNC02YmM1YzAyOGU2ZTUALgAAA8tzRcX8LyRElN24LlY4kT8BANvL1mNV1MlMlFL"
                "yPGtwD6gAAAIBDAAAAA%3D%3D')/messages/$entity"
            ),
            "@odata.etag": "W/\"CQAAABYAAADby9ZjVdTJTJRS8jxrcA+oAAP3A7Hj\"",
            "id": (
                "AAMkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMDI4ZTZlNQBGAAAAAADLc0XF"
                "-C8kRJTduC5WOJE-BwDby9ZjVdTJTJRS8jxrcA_oAALg_Vq3AADby9ZjVdTJT"
                "JRS8jxrcA_oAAP1qhPJAAA="
            ),
            "createdDateTime": "2023-12-28T10:15:34Z",
            "lastModifiedDateTime": "2024-01-02T12:45:10Z",
            "changeKey": "CQAAABYAAADby9ZjVdTJTJRS8jxrcA+oAAP3A7Hj",
            "categories": [],
            "receivedDateTime": "2023-12-28T10:15:35Z",
            "sentDateTime": "2023-12-28T10:15:31Z",
            "hasAttachments": True,
            "internetMessageId": (
                "<DB9PR05MB79627ADBED8E2BBAE6B596FBBE9EA@DB9PR05MB7962."
                "eurprd05.prod.outlook.com>"
            ),
            "subject": "Testing Mail wait for user to reply",
            "bodyPreview": "Reply",
            "importance": "normal",
            "parentFolderId": (
                "AAMkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMDI4ZTZlNQAuAAAAAADLc0"
                "XF-C8kRJTduC5WOJE-AQDby9ZjVdTJTJRS8jxrcA_oAALg_Vq3AAA="
            ),
            "conversationId": (
                "AAQkADU0MDJjNjJkLTc3MzAtNGM5My04ZjM0LTZiYzVjMDI4ZTZ"
                "lNQAQANYl8CFFq3VBmiUazocJzLc="
            ),
            "conversationIndex": "AQHaOXa81iXwIUWrdUGaJRrOhwnMtw==",
            "isDeliveryReceiptRequested": False,
            "isReadReceiptRequested": False,
            "isRead": True,
            "isDraft": False,
            "moveToInbox": False,
            "moveToJunk": False,
            "webLink": (
                "https://outlook.office365.com/owa/?ItemID=AAMkADU0MDJjNjJkLTc3MzAtN"
                "GM5My04ZjM0LTZiYzVjMDI4ZTZlNQBGAAAAAADLc0XF%2FC8kRJTduC5WOJE%2FBw"
                "Dby9ZjVdTJTJRS8jxrcA%2BoAALg%2BVq3AADby9ZjVdTJTJRS8jxrcA%2BoAAP1qh"
                "PJAAA%3D&exvsurl=1&viewmodel=ReadMessageItem"
            ),
            "inferenceClassification": "focused",
            "body": {
                "contentType": "html",
                "content": (
                    "<html><head>\r\n<meta http-equiv=\"Content-Type\" content=\""
                    "text/html; charset=utf-8\"><style type=\"text/css\" "
                    "style=\"display:none\">\r\n<!--\r\np\r\n\t{margi"
                    "n-top:0;\r\n\tmargin-bottom:0}\r\n-->\r\n</style></head><bod"
                    "y dir=\"ltr\"><div class=\"elementToProof\" style=\"font-family"
                    ":Aptos,Aptos_EmbeddedFont,Aptos_MSFontService,Calibri,Helvetica,"
                    "sans-serif; font-size:12pt; color:rgb(0,0,0)\">Reply<br></div>"
                    "</body></html>"
                )
            },
            "sender": {
                "emailAddress":{
                    "name": (
                        "\u05d2'\u05d9\u05d9\u05de\u05e1 \u05d1\u05d5\u05e0\u05d3"
                    ),
                    "address": "abc@example.com"
                }
            },
            "from": {
                "emailAddress": {
                    "name": "\u05d2'\u05d9\u05d9\u05de\u05e1 \u05d1\u05d5\u05e0\u05d3",
                    "address": "abc@example.com"
                }
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "name": (
                            "\u05d2'\u05d9\u05d9\u05de\u05e1 \u05d1\u05d5\u05e0\u05d3"
                        ),
                        "address": "abc@example.com"
                    }
                }
            ],
            "ccRecipients": [],
            "bccRecipients": [],
            "replyTo": [],
            "flag": {"flagStatus": "notFlagged"}
        }
    ]
}

ACTION_IN_PROGRESS_OUTPUT = ActionOutput(
    output_message=INPROGRESS_OUTPUT_MESSAGE,
    result_value=json.dumps(ACTION_INPROGRESS_RESULT_VALUE),
    execution_state=ExecutionState.IN_PROGRESS,
    json_output=None,
)

ACTION_FAILURE_OUTPUT = ActionOutput(
    output_message=FAILURE_OUTPUT_MESSAGE,
    result_value=False,
    execution_state=ExecutionState.FAILED,
    json_output=None,
)

SCRIPT_DEADLINE_TIME = datetime.datetime.now() + datetime.timedelta(minutes=10)


@set_metadata(
    parameters={
        "Delete In Mailbox": "Default Mailbox",
        "Folder Name": "Inbox",
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
def test_delete_email_success(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    siemplify: SiemplifyAction = SiemplifyAction()
    DeleteEmailAction(siemplify).run()

    assert DEFAULT_EMAIL.id not in ms_graph_mail.get_emails()
    assert len(script_session.request_history) == 5
    assert action_output.results == ACTION_SUCCESS_OUTPUT


@set_metadata(
    parameters={
        "Delete In Mailbox": "Default Mailbox, abcd@gmail.com",
        "Folder Name": "Inbox",
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
def test_delete_email_inprogress(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    siemplify: SiemplifyAction = SiemplifyAction()

    DeleteEmailAction(siemplify).run()

    assert DEFAULT_EMAIL.id not in ms_graph_mail.get_emails()
    assert len(script_session.request_history) == 6
    assert action_output.results == ACTION_IN_PROGRESS_OUTPUT


@set_metadata(
    parameters={
        "Delete In Mailbox": "Default Mailbox, abcd@gmail.com",
        "Folder Name": "Inbox",
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
def test_delete_email_failed(
    ms_graph_mail: MicrosoftGraphMailDelegated,
    script_session: MsGraphSession,
    action_output: MockActionOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_email(DEFAULT_EMAIL)

    siemplify: SiemplifyAction = SiemplifyAction()

    DeleteEmailAction(siemplify).run()

    assert DEFAULT_EMAIL == ms_graph_mail.get_email(DEFAULT_EMAIL.id)
    assert len(script_session.request_history) == 7
    assert action_output.results == ACTION_FAILURE_OUTPUT
