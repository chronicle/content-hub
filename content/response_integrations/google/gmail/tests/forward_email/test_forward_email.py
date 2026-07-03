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

from ...actions.ForwardEmail import (
    ForwardEmail,
    SUCCESS_MESSAGE,
    MESSAGE_NOT_FOUND,
)
import gmail.core.GoogleGmailConsts as Constants

from ...tests.common import CONFIG, MOCK_DATA
from ...tests.core.async_session import GoogleGmailAsyncSession
from ...tests.core.google_gmail import GoogleGmail
from ...tests.utils import (
    assert_all_get_message,
    assert_all_get_attachment,
    assert_all_list_messages,
    assert_all_send_message,
    create_test_attachment,
    delete_test_attachments
)
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR_PREFIX = (
    f"Error executing action \"{Constants.FORWARD_EMAIL_SCRIPT_NAME}\"\nReason:"
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

ACTION_CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
ACTION_CONFIG: SingleJson = get_def_file_content(ACTION_CONFIG_PATH)

ACTION_CONFIG_WITH_MESSAGE_ID = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_MESSAGE_ID["Internet Message ID"] = (
    "\u003cCAAfJ0RhhZBGtbvyx1YfAUQcWByMP2UuG2oKk2mEdZ_XCiEuLRw@mail.gmail.com\u003e"
)

ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS = ACTION_CONFIG_WITH_MESSAGE_ID.copy()
ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS["Send To"] = (
    "test1@mailbox.com, test2@mailbox.com"
)
ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS["CC"] = (
    "testCC1@mailbox.com, testCC2@mailbox.com"
)
ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS["BCC"] = (
    "testBCC1@mailbox.com, testBCC2@mailbox.com"
)

ACTION_CONFIG_WITH_ATTACHMENTS = ACTION_CONFIG_WITH_MESSAGE_ID.copy()
ACTION_CONFIG_WITH_ATTACHMENTS["Attachments Paths"] = (
    ",".join(
        create_test_attachment(ATTACHMENT_PATH, file_name)
        for file_name in (
            f"forward_{ATTACHMENT_NAME}",
            f"forward_{ATTACHMENT_NAME_WITH_UNKNOWN_TYPE}"
        )
    )
)

ACTION_CONFIG_WITH_EMAIL_WITH_ATTACHMENTS = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_EMAIL_WITH_ATTACHMENTS["Internet Message ID"] = (
    "\u003cCAGj5zfcu0Ms=wCrKQzpQstWjECFHX+O5VYcOBWQVjx=vBA3TaA@mail.gmail.com\u003e"
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
        ForwardEmail(script_name=Constants.FORWARD_EMAIL_SCRIPT_NAME).run()

        assert len(gmail_script_session.request_history) == 0
        assert action_output.results == ActionOutput(
            output_message=NO_CREDS_OUTPUT_MESSAGE,
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG
    )
    def test_invalid_email(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput,
    ) -> None:
        ForwardEmail(script_name=Constants.FORWARD_EMAIL_SCRIPT_NAME).run()

        assert len(gmail_script_session.request_history) == 1
        assert (
            MESSAGE_NOT_FOUND.format(ACTION_CONFIG["Internet Message ID"])
            in action_output.results.output_message
        )
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.json_output is None


class TestForwardEmail:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_with_no_params(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        action = ForwardEmail(script_name=Constants.FORWARD_EMAIL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 5
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=3)
        assert_all_send_message(gmail_script_session.request_history, start=3, stop=4)
        assert_all_get_message(gmail_script_session.request_history, start=4)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.output_message ==
            SUCCESS_MESSAGE.format(ACTION_CONFIG_WITH_MESSAGE_ID["Internet Message ID"])
        )
        assert action_output.results.result_value is True
        assert "message_id" in action_output.results.json_output.json_result

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_COMMA_SEPARATED_PARAMS
    )
    def test_with_csv_reply_to(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        action = ForwardEmail(script_name=Constants.FORWARD_EMAIL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 5
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=3)
        assert_all_send_message(gmail_script_session.request_history, start=3, stop=4)
        assert_all_get_message(gmail_script_session.request_history, start=4)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.output_message ==
            SUCCESS_MESSAGE.format(ACTION_CONFIG_WITH_MESSAGE_ID["Internet Message ID"])
        )
        assert action_output.results.result_value is True
        assert "message_id" in action_output.results.json_output.json_result

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_ATTACHMENTS
    )
    def test_with_attachments(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        action = ForwardEmail(script_name=Constants.FORWARD_EMAIL_SCRIPT_NAME)
        action.run()
        delete_test_attachments(ACTION_CONFIG_WITH_ATTACHMENTS["Attachments Paths"])

        assert len(gmail_script_session.request_history) == 5
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=3)
        assert_all_send_message(gmail_script_session.request_history, start=3, stop=4)
        assert_all_get_message(gmail_script_session.request_history, start=4)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.output_message ==
            SUCCESS_MESSAGE.format(ACTION_CONFIG_WITH_MESSAGE_ID["Internet Message ID"])
        )
        assert action_output.results.result_value is True
        assert "message_id" in action_output.results.json_output.json_result

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_EMAIL_WITH_ATTACHMENTS
    )
    def test_with_attachments_in_original_email(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(
            MOCK_DATA["mail_without_attachments"] + MOCK_DATA["mail_with_eml"]
        )
        google_gmail.set_attachments(MOCK_DATA["attachments"])
        action = ForwardEmail(script_name=Constants.FORWARD_EMAIL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 7
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=3)
        assert_all_get_attachment(gmail_script_session.request_history, start=3, stop=5)
        assert_all_send_message(gmail_script_session.request_history, start=5, stop=6)
        assert_all_get_message(gmail_script_session.request_history, start=6)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.output_message ==
            SUCCESS_MESSAGE.format(
                ACTION_CONFIG_WITH_EMAIL_WITH_ATTACHMENTS["Internet Message ID"]
            )
        )
        assert action_output.results.result_value is True
        assert "message_id" in action_output.results.json_output.json_result
