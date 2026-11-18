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

from gmail.actions.SendEmail import (
    SendEmail,
    SUCCESS_MESSAGE,
)
import gmail.core.GoogleGmailConsts as Constants

from gmail.tests.common import CONFIG, MOCK_DATA
from gmail.tests.core.async_session import GoogleGmailAsyncSession
from gmail.tests.core.google_gmail import GoogleGmail
from gmail.tests.utils import (
    assert_all_get_message,
    assert_all_send_message,
    create_test_attachment,
    delete_test_attachments
)
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR_PREFIX = (
    "Failed to send email!\nReason:"
)
NO_CREDS_OUTPUT_MESSAGE = (
    f"{ERROR_PREFIX} No service account or workload identity email were provided."
)
INVALID_EMAIL_OUTPUT_MESSAGE = (
    f"{ERROR_PREFIX} Impersonation is not allowed for the provided "
    "service account. Please check the \"Service Account Token Creator\" role to the "
    "service account: "
)

ATTACHMENT_PATH = "test_attachments"
ATTACHMENT_NAME = "test_attachment.txt"
ATTACHMENT_NAME_WITH_UNKNOWN_TYPE = "test_attachment.log"

CONFIG_WITHOUT_CREDS = CONFIG.copy()
CONFIG_WITHOUT_CREDS["Workload Identity Email"] = None

CONFIG_WITH_INVALID_EMAIL = CONFIG.copy()
CONFIG_WITH_INVALID_EMAIL["Workload Identity Email"] = "invalid-sa@domain.com"

ACTION_CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
ACTION_CONFIG: SingleJson = get_def_file_content(ACTION_CONFIG_PATH)

ACTION_CONFIG_WITH_ALL_PARAMS = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_ALL_PARAMS["CC"] = "testCC@mailbox.com"
ACTION_CONFIG_WITH_ALL_PARAMS["BCC"] = "testBCC@mailbox.com"
ACTION_CONFIG_WITH_ALL_PARAMS["Reply-To Recipients"] = "testReplyTo@mailbox.com"

ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS["Send To"] = (
    "test1@mailbox.com, test2@mailbox.com"
)
ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS["CC"] = (
    "testCC1@mailbox.com, testCC2@mailbox.com"
)
ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS["BCC"] = (
    "testBCC1@mailbox.com, testBCC2@mailbox.com"
)
ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS["Reply-To Recipients"] = (
    "testReplyTo1@mailbox.com, testReplyTo2@mailbox.com"
)

ACTION_CONFIG_WITH_ATTACHMENTS = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_ATTACHMENTS["Attachments Paths"] = (
    ",".join(
        create_test_attachment(
            ATTACHMENT_PATH, file_name
        ) for file_name in (ATTACHMENT_NAME, ATTACHMENT_NAME_WITH_UNKNOWN_TYPE)
    )
)


class TestSendEmailAuth:

    @set_metadata(
        integration_config=CONFIG_WITHOUT_CREDS,
        parameters=ACTION_CONFIG
    )
    def test_without_creds(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput,
    ) -> None:
        SendEmail(script_name=Constants.SEND_EMAIL_SCRIPT_NAME).run()

        assert len(gmail_script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=NO_CREDS_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG_WITH_INVALID_EMAIL,
        parameters=ACTION_CONFIG
    )
    def test_invalid_email(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput,
    ) -> None:
        SendEmail(script_name=Constants.SEND_EMAIL_SCRIPT_NAME).run()

        assert len(gmail_script_session.request_history) == 0
        assert (
            INVALID_EMAIL_OUTPUT_MESSAGE in action_output.results.output_message
        )
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.json_output is None


class TestSendEmail:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG
    )
    def test_send_email_with_mandatory_params(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        action = SendEmail(script_name=Constants.SEND_EMAIL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_all_send_message(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == SUCCESS_MESSAGE
        assert action_output.results.result_value is True
        assert "message_id" in action_output.results.json_output.json_result

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_ALL_PARAMS
    )
    def test_send_email_with_all_params(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        action = SendEmail(script_name=Constants.SEND_EMAIL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_all_send_message(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == SUCCESS_MESSAGE
        assert action_output.results.result_value is True
        assert "message_id" in action_output.results.json_output.json_result

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS
    )
    def test_send_email_with_comma_separated_params(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        action = SendEmail(script_name=Constants.SEND_EMAIL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_all_send_message(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == SUCCESS_MESSAGE
        assert action_output.results.result_value is True
        assert "message_id" in action_output.results.json_output.json_result

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_ATTACHMENTS
    )
    def test_send_email_with_attachments(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        action = SendEmail(script_name=Constants.SEND_EMAIL_SCRIPT_NAME)
        action.run()
        delete_test_attachments(ACTION_CONFIG_WITH_ATTACHMENTS["Attachments Paths"])

        assert len(gmail_script_session.request_history) == 3
        assert_all_send_message(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.output_message == SUCCESS_MESSAGE
        assert action_output.results.result_value is True
        assert "message_id" in action_output.results.json_output.json_result
