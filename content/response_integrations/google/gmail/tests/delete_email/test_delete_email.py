# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import pathlib

from TIPCommon.base.action import ExecutionState
from TIPCommon.base.data_models import ActionOutput, ActionJsonOutput
from TIPCommon.types import SingleJson

from gmail.actions.DeleteEmail import (
    DeleteEmail,
    EMPTY_PARAMS_MESSAGE,
    NO_MAILBOXES_FOUND_MESSAGE,
    NO_MESSAGES_DELETED_MESSAGE,
    NOT_FOUND_MAILBOX_MESSAGE,
    SUCCESS_MESSAGE,
    UNFINISHED_MAILBOX_MESSAGE,
)
import gmail.core.GoogleGmailConsts as Constants

from gmail.tests.common import CONFIG, MOCK_DATA
from gmail.tests.core.async_session import GoogleGmailAsyncSession
from gmail.tests.core.google_gmail import GoogleGmail
from gmail.tests.utils import (
    assert_all_list_messages,
    assert_all_delete_messages,
    assert_all_trash_messages,
    init_async_action,
)
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR = (
    f"Error executing action \"{Constants.DELETE_EMAIL_SCRIPT_NAME}\"\nReason:"
)
NO_CREDS_OUTPUT_MESSAGE = (
    f"{ERROR} No service account or workload identity email were provided."
)

CONFIG_WITHOUT_CREDS = CONFIG.copy()
CONFIG_WITHOUT_CREDS["Workload Identity Email"] = None

CONFIG_WITH_INVALID_EMAIL = CONFIG.copy()
CONFIG_WITH_INVALID_EMAIL["Workload Identity Email"] = "invalid-sa@domain.com"

ACTION_CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
ACTION_CONFIG: SingleJson = get_def_file_content(ACTION_CONFIG_PATH)

ACTION_CONFIG_WITH_EMPTY_FILTER = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_EMPTY_FILTER["Labels Filter"] = ""

ACTION_CONFIG_WITH_MAILBOXES = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_MAILBOXES["Mailbox"] = "test@mailbox.com"

ACTION_CONFIG_WITH_INVALID_MAILBOXES = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_INVALID_MAILBOXES["Mailbox"] = "invalid@mailbox.com"

ACTION_CONFIG_WITH_MIXED_MAILBOXES = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_MIXED_MAILBOXES["Mailbox"] = (
    "test@mailbox.com, invalid@mailbox.com"
)

ACTION_CONFIG_WITH_TIMEFRAME = ACTION_CONFIG_WITH_MAILBOXES.copy()
ACTION_CONFIG_WITH_TIMEFRAME["Time Frame (minutes)"] = 1

ACTION_CONFIG_WITH_MESSAGE_ID = ACTION_CONFIG_WITH_MAILBOXES.copy()
ACTION_CONFIG_WITH_MESSAGE_ID["Internet Message ID"] = (
    "\u003cCAAfJ0RhhZBGtbvyx1YfAUQcWByMP2UuG2oKk2mEdZ_XCiEuLRw@mail.gmail.com\u003e"
)

ACTION_CONFIG_WITH_TRASH_AND_MESSAGE_ID = ACTION_CONFIG_WITH_MESSAGE_ID.copy()
ACTION_CONFIG_WITH_TRASH_AND_MESSAGE_ID["Move to Trash"] = True


class TestDeleteEmailAuth:

    @set_metadata(
        integration_config=CONFIG_WITHOUT_CREDS,
        parameters=ACTION_CONFIG
    )
    def test_without_creds(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput,
    ) -> None:
        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME
        )
        action.run()

        assert len(gmail_script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=NO_CREDS_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )


class TestDeleteEmailInvalidParams:

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG
    )
    def test_without_params(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput,
    ) -> None:
        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert action_output.results == ActionOutput(
            output_message=NO_MESSAGES_DELETED_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MAILBOXES
    )
    def test_no_messages_deleted(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput,
    ) -> None:
        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert action_output.results == ActionOutput(
            output_message=NO_MESSAGES_DELETED_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID,
    )
    def test_invalid_message_id(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert action_output.results == ActionOutput(
            output_message=NO_MESSAGES_DELETED_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_EMPTY_FILTER
    )
    def test_delete_message_empty_filter(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])

        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME
        )
        action.run()

        assert len(gmail_script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=F"{ERROR} {EMPTY_PARAMS_MESSAGE}",
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_INVALID_MAILBOXES
    )
    def test_no_mailbox_found(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput,
    ) -> None:
        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert action_output.results == ActionOutput(
            output_message=(
                f"{ERROR} {NO_MAILBOXES_FOUND_MESSAGE.format('invalid@mailbox.com')}"
            ),
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )


class TestDeleteEmailMessageId:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_delete_message_by_message_id(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])

        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME
        )
        action.run()

        assert len(gmail_script_session.request_history) == 2
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_delete_messages(gmail_script_session.request_history, start=1)

        assert action_output.results == ActionOutput(
            output_message=SUCCESS_MESSAGE.format(
                "Deleted 1 out of 1 in test@mailbox.com."
            ),
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result=[
                    {
                        "Entity": "test@mailbox.com",
                        "EntityResult": ["19050407063955c1"]
                    }
                ]
            ),
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_TRASH_AND_MESSAGE_ID
    )
    def test_trash_message_by_message_id(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])

        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME
        )
        action.run()

        assert len(gmail_script_session.request_history) == 2
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_trash_messages(gmail_script_session.request_history, start=1)

        assert action_output.results == ActionOutput(
            output_message=SUCCESS_MESSAGE.format(
                "Deleted 1 out of 1 in test@mailbox.com."
            ),
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result=[
                    {
                        "Entity": "test@mailbox.com",
                        "EntityResult": ["19050407063955c1"]
                    }
                ]
            ),
        )


class TestDeleteEmailFilter:

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MIXED_MAILBOXES
    )
    def test_delete_message_valid_invalid_mailbox(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])

        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME
        )
        action.run()

        assert len(gmail_script_session.request_history) == 4
        assert_all_list_messages(gmail_script_session.request_history, stop=2)
        assert_all_delete_messages(gmail_script_session.request_history, start=2)

        success_message_part = (
            SUCCESS_MESSAGE.format("Deleted 2 out of 2 in test@mailbox.com.")
        )
        assert action_output.results == ActionOutput(
            output_message=(
                f"{success_message_part}"
                f"{NOT_FOUND_MAILBOX_MESSAGE.format('invalid@mailbox.com')}"
            ),
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result=[
                    {
                        "Entity": "test@mailbox.com",
                        "EntityResult": [
                            "19050407063955c1",
                            "190504071f10bfdb"
                        ]
                    }
                ]
            ),
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_TIMEFRAME
    )
    def test_delete_message_time_filter(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"][:1])
        google_gmail.set_messages(
            MOCK_DATA["mail_without_attachments"][1:],
            set_ts_to_now=True
        )

        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME
        )
        action.run()

        assert len(gmail_script_session.request_history) == 2
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_delete_messages(gmail_script_session.request_history, start=1)

        assert action_output.results == ActionOutput(
            output_message=SUCCESS_MESSAGE.format(
                "Deleted 1 out of 1 in test@mailbox.com."
            ),
            result_value=True,
            execution_state=ExecutionState.COMPLETED,
            json_output=ActionJsonOutput(
                json_result=[
                    {
                        "Entity": "test@mailbox.com",
                        "EntityResult": ["190504071f10bfdb"]
                    }
                ]
            ),
        )


class TestAsyncTimeout:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_delete_timeout(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        action = init_async_action(
            DeleteEmail,
            script_name=Constants.DELETE_EMAIL_SCRIPT_NAME,
            async_timeout_ms=1
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert action_output.results == ActionOutput(
            output_message=(
                f"{ERROR} {UNFINISHED_MAILBOX_MESSAGE.format('test@mailbox.com')}"
            ),
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )
