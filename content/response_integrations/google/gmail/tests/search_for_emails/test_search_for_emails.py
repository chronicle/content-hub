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
from TIPCommon.base.data_models import ActionOutput
from TIPCommon.types import SingleJson

from gmail.actions.SearchForEmails import (
    SearchForEmails,
    NO_MESSAGES_FOUND_MESSAGE,
    NOT_FOUND_MAILBOX_MESSAGE,
    NO_MAILBOXES_FOUND_MESSAGE,
    SUCCESS_MESSAGE,
    UNFINISHED_MAILBOX_MESSAGE,
)
import gmail.core.GoogleGmailConsts as Constants

from gmail.tests.common import CONFIG, MOCK_DATA
from gmail.tests.core.async_session import GoogleGmailAsyncSession
from gmail.tests.core.google_gmail import GoogleGmail
from gmail.tests.utils import (
    assert_all_get_message,
    assert_all_list_messages,
    init_async_action,
)
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR = (
    f"Error executing action \"{Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME}\"\nReason:"
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


class TestAuth:

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
            SearchForEmails,
            script_name=Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=NO_CREDS_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )


class TestInvalidParams:

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
            SearchForEmails,
            script_name=Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert action_output.results == ActionOutput(
            output_message=NO_MESSAGES_FOUND_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MAILBOXES
    )
    def test_no_messages_found(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput,
    ) -> None:
        action = init_async_action(
            SearchForEmails,
            script_name=Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert action_output.results == ActionOutput(
            output_message=NO_MESSAGES_FOUND_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.COMPLETED,
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
            SearchForEmails,
            script_name=Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert (
            action_output.results.output_message ==
            f"{ERROR} {NO_MAILBOXES_FOUND_MESSAGE.format('invalid@mailbox.com')}"
        )
        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_invalid_message_id(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        action = init_async_action(
            SearchForEmails,
            script_name=Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert action_output.results == ActionOutput(
            output_message=NO_MESSAGES_FOUND_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.COMPLETED,
            json_output=None,
        )


class TestMessageID:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_search_message_by_message_id(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])

        action = init_async_action(
            SearchForEmails,
            script_name=Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 2
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1)

        assert action_output.results.output_message == (
            SUCCESS_MESSAGE.format(
                "Fetched 1 out of 1 in test@mailbox.com."
            )
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED


class TestFilter:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MAILBOXES
    )
    def test_search_message_empty_filter(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])

        action = init_async_action(
            SearchForEmails,
            script_name=Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1)

        assert action_output.results.output_message == (
            SUCCESS_MESSAGE.format(
                "Fetched 2 out of 2 in test@mailbox.com."
            )
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MIXED_MAILBOXES
    )
    def test_search_message_valid_invalid_mailbox(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])

        action = init_async_action(
            SearchForEmails,
            script_name=Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 4
        assert_all_list_messages(gmail_script_session.request_history, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2)

        success_message_part = SUCCESS_MESSAGE.format(
            "Fetched 2 out of 2 in test@mailbox.com."
        )
        assert action_output.results.output_message == (
            f"{success_message_part}"
            f"{NOT_FOUND_MAILBOX_MESSAGE.format('invalid@mailbox.com')}"
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_TIMEFRAME
    )
    def test_search_message_time_filter(
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
            SearchForEmails,
            script_name=Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 2
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1)

        assert action_output.results.output_message == (
            SUCCESS_MESSAGE.format(
                "Fetched 1 out of 1 in test@mailbox.com."
            )
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED


class TestAsyncTimeout:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_search_timeout(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        action = init_async_action(
            SearchForEmails,
            script_name=Constants.SEARCH_FOR_EMAILS_SCRIPT_NAME,
            async_timeout_ms=1
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert (
            f"{ERROR} {UNFINISHED_MAILBOX_MESSAGE.format('test@mailbox.com')}"
            == action_output.results.output_message
        )
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
