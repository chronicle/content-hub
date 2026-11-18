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

from gmail.actions.WaitForThreadReply import (
    WaitForThreadReply,
    ASYNC_TIMEOUT_MESSAGE,
    ASYNC_TIMOUT_WITH_SOME_FETCHED,
    MESSAGE_NOT_FOUND,
    PENDING_MESSAGE,
    SUCCESS_MESSAGE,
)
import gmail.core.GoogleGmailConsts as Constants

from gmail.tests.common import CONFIG, MOCK_DATA
from gmail.tests.core.async_session import GoogleGmailAsyncSession
from gmail.tests.core.google_gmail import GoogleGmail
from gmail.tests.utils import (
    assert_all_get_message,
    assert_all_list_messages,
    assert_get_thread,
    init_async_action,
)
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR_PREFIX = (
    f"Error executing action \"{Constants.WAIT_FOR_THREAD_REPLY_SCRIPT_NAME}\"\n"
    "Reason:"
)
NO_CREDS_OUTPUT_MESSAGE = (
    f"{ERROR_PREFIX} No service account or workload identity email were provided."
)

CONFIG_WITHOUT_CREDS = CONFIG.copy()
CONFIG_WITHOUT_CREDS["Workload Identity Email"] = None

CONFIG_WITH_INVALID_EMAIL = CONFIG.copy()
CONFIG_WITH_INVALID_EMAIL["Workload Identity Email"] = "invalid-sa@domain.com"

ACTION_CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
ACTION_CONFIG: SingleJson = get_def_file_content(ACTION_CONFIG_PATH)

ACTION_CONFIG_WITH_INVALID_MAILBOX = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_INVALID_MAILBOX["Mailbox"] = "invalid@mailbox.com"

ACTION_CONFIG_WITH_MESSAGE_ID = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_MESSAGE_ID["Internet Message ID"] = (
    "\u003cCAAfJ0RhhZBGtbvyx1YfAUQcWByMP2UuG2oKk2mEdZ_XCiEuLRw@mail.gmail.com\u003e"
)

ACTION_CONFIG_WITH_NO_WAIT = ACTION_CONFIG_WITH_MESSAGE_ID.copy()
ACTION_CONFIG_WITH_NO_WAIT["Wait for All Recipients to Reply"] = False


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
            WaitForThreadReply,
            script_name=Constants.WAIT_FOR_THREAD_REPLY_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=NO_CREDS_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_INVALID_MAILBOX
    )
    def test_mailbox_not_found(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput,
    ) -> None:
        action = init_async_action(
            WaitForThreadReply,
            script_name=Constants.WAIT_FOR_THREAD_REPLY_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history)

        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED


class TestMessageID:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG
    )
    def test_email_not_found(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput,
    ) -> None:
        action = init_async_action(
            WaitForThreadReply,
            script_name=Constants.WAIT_FOR_THREAD_REPLY_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 1
        assert_all_list_messages(gmail_script_session.request_history, stop=1)

        assert (
            MESSAGE_NOT_FOUND.format(ACTION_CONFIG["Internet Message ID"])
            in action_output.results.output_message
        )
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED


class TestReplies:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_no_replies(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        google_gmail.add_thread(MOCK_DATA["mail_without_attachments"][:1])

        action = init_async_action(
            WaitForThreadReply,
            script_name=Constants.WAIT_FOR_THREAD_REPLY_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1)
        assert_get_thread(gmail_script_session.request_history, 2)

        assert PENDING_MESSAGE[:-3] in action_output.results.output_message
        assert all(
            recipient in action_output.results.output_message for recipient in
            ("test-guy@smplylab.com", "test-folk@google.com", "test-boy@google.com")
        )
        assert action_output.results.result_value
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_email_found_single_reply(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        google_gmail.add_thread(MOCK_DATA["mail_without_attachments"])

        action = init_async_action(
            WaitForThreadReply,
            script_name=Constants.WAIT_FOR_THREAD_REPLY_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 4
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=2)
        assert_get_thread(gmail_script_session.request_history, 2)
        assert_all_get_message(gmail_script_session.request_history, start=3)

        assert PENDING_MESSAGE[:-3] in action_output.results.output_message
        assert all(
            recipient in action_output.results.output_message for recipient in
            ("test-folk@google.com", "test-boy@google.com")
        )
        assert action_output.results.result_value
        assert action_output.results.execution_state == ExecutionState.IN_PROGRESS

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_NO_WAIT
    )
    def test_email_found_single_reply_no_wait(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        google_gmail.add_thread(MOCK_DATA["mail_without_attachments"])

        action = init_async_action(
            WaitForThreadReply,
            script_name=Constants.WAIT_FOR_THREAD_REPLY_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 4
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=2)
        assert_get_thread(gmail_script_session.request_history, 2)
        assert_all_get_message(gmail_script_session.request_history, start=3)

        assert (
            SUCCESS_MESSAGE.format("test-guy@smplylab.com")
            in action_output.results.output_message
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_email_found_all_replies(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(
            MOCK_DATA["mail_without_attachments"] +
            MOCK_DATA["mail_with_eml"] +
            MOCK_DATA["mail_with_files"]
        )
        google_gmail.add_thread(
            MOCK_DATA["mail_without_attachments"] +
            MOCK_DATA["mail_with_eml"] +
            MOCK_DATA["mail_with_files"]
        )

        action = init_async_action(
            WaitForThreadReply,
            script_name=Constants.WAIT_FOR_THREAD_REPLY_SCRIPT_NAME,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 6
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=2)
        assert_get_thread(gmail_script_session.request_history, 2)
        assert_all_get_message(gmail_script_session.request_history, start=3)

        assert SUCCESS_MESSAGE[:-5] in action_output.results.output_message
        assert all(
            recipient in action_output.results.output_message for recipient in
            ("test-guy@smplylab.com", "test-folk@google.com", "test-boy@google.com")
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED


class TestAsyncTimeout:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_no_replies(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        google_gmail.add_thread(MOCK_DATA["mail_without_attachments"][:1])

        action = init_async_action(
            WaitForThreadReply,
            script_name=Constants.WAIT_FOR_THREAD_REPLY_SCRIPT_NAME,
            async_timeout_ms=0,
        )
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1)
        assert_get_thread(gmail_script_session.request_history, 2)

        assert ASYNC_TIMEOUT_MESSAGE in action_output.results.output_message
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_email_found_single_reply(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        google_gmail.add_thread(MOCK_DATA["mail_without_attachments"])

        action = init_async_action(
            WaitForThreadReply,
            script_name=Constants.WAIT_FOR_THREAD_REPLY_SCRIPT_NAME,
        )
        action.is_approaching_async_timeout = lambda: True
        action.run()

        assert len(gmail_script_session.request_history) == 4
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=2)
        assert_get_thread(gmail_script_session.request_history, 2)
        assert_all_get_message(gmail_script_session.request_history, start=3)

        assert (
            SUCCESS_MESSAGE.format("test-guy@smplylab.com") in
            action_output.results.output_message
        )
        assert (
            ASYNC_TIMOUT_WITH_SOME_FETCHED.format(
                "test-boy@google.com, test-folk@google.com"
            ) in action_output.results.output_message or
            ASYNC_TIMOUT_WITH_SOME_FETCHED.format(
                "test-folk@google.com, test-boy@google.com"
            ) in action_output.results.output_message
        )
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
