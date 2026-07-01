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

from ...actions.SaveEmailToTheCase import (
    SaveEmailToTheCase,
    SUCCESS_MESSAGE,
    SUCCESS_ATTACHMENTS,
    MESSAGE_NOT_FOUND,
    NO_ATTACHMENTS_SAVED,
)
import gmail.core.GoogleGmailConsts as Constants

from ...tests.common import CONFIG, MOCK_DATA
from ...tests.core.async_session import GoogleGmailAsyncSession
from ...tests.core.google_gmail import GoogleGmail
from ...tests.core.session import GoogleGmailSession
from ...tests.utils import (
    assert_all_get_message,
    assert_all_get_attachment,
    assert_all_list_messages,
    assert_all_add_evidence,
)
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR_PREFIX = (
    f"Error executing action \"{Constants.SAVE_EMAIL_TO_THE_CASE}\"\nReason:"
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

ACTION_CONFIG_WITH_BASE64_ENCODE = ACTION_CONFIG_WITH_MESSAGE_ID.copy()
ACTION_CONFIG_WITH_BASE64_ENCODE["Base64 Encode"] = "true"

ACTION_CONFIG_WITH_ATTACHMENTS = ACTION_CONFIG.copy()
ACTION_CONFIG_WITH_ATTACHMENTS["Save Only Email Attachments"] = "true"
ACTION_CONFIG_WITH_ATTACHMENTS["Internet Message ID"] = (
    "\u003ccalendar-39612cc2-b751-4aae-ab87-cd85b1b03eb2@google.com\u003e"
)

ACTION_CONFIG_WITH_ATTACHMENTS_FILTERED = ACTION_CONFIG_WITH_ATTACHMENTS.copy()
ACTION_CONFIG_WITH_ATTACHMENTS_FILTERED["Attachment To Save"] = "invalid.txt"


ACTION_CONFIG_WITH_ATTACHMENTS_AND_ENCODE = (
    ACTION_CONFIG_WITH_ATTACHMENTS.copy()
)
ACTION_CONFIG_WITH_ATTACHMENTS_AND_ENCODE["Base64 Encode"] = "true"


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
        SaveEmailToTheCase(script_name=Constants.SAVE_EMAIL_TO_THE_CASE).run()

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
        SaveEmailToTheCase(script_name=Constants.SAVE_EMAIL_TO_THE_CASE).run()

        assert len(gmail_script_session.request_history) == 1
        assert (
            MESSAGE_NOT_FOUND.format(ACTION_CONFIG["Internet Message ID"])
            in action_output.results.output_message
        )
        assert action_output.results.result_value is False
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.json_output is None


class TestSaveEmail:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_with_no_params(
            self,
            google_gmail: GoogleGmail,
            gmail_sync_session: GoogleGmailSession,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        action = SaveEmailToTheCase(script_name=Constants.SAVE_EMAIL_TO_THE_CASE)
        action.soar_action.session = gmail_sync_session
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=3)

        assert len(gmail_sync_session.request_history) == 1
        assert_all_add_evidence(gmail_sync_session.request_history)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.output_message ==
            SUCCESS_MESSAGE.format(ACTION_CONFIG_WITH_MESSAGE_ID["Internet Message ID"])
        )
        assert action_output.results.result_value is True
        assert "mime_content" not in action_output.results.json_output.json_result

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_BASE64_ENCODE
    )
    def test_with_base64_encode(
            self,
            google_gmail: GoogleGmail,
            gmail_sync_session: GoogleGmailSession,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])
        action = SaveEmailToTheCase(script_name=Constants.SAVE_EMAIL_TO_THE_CASE)
        action.soar_action.session = gmail_sync_session
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=3)

        assert len(gmail_sync_session.request_history) == 1
        assert_all_add_evidence(gmail_sync_session.request_history)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.output_message ==
            SUCCESS_MESSAGE.format(ACTION_CONFIG_WITH_MESSAGE_ID["Internet Message ID"])
        )
        assert action_output.results.result_value is True
        assert "mime_content" in action_output.results.json_output.json_result

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_ATTACHMENTS_FILTERED
    )
    def test_with_attachments_filtered(
            self,
            google_gmail: GoogleGmail,
            gmail_sync_session: GoogleGmailSession,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_with_files"])
        google_gmail.set_attachments(MOCK_DATA["attachments"])
        action = SaveEmailToTheCase(script_name=Constants.SAVE_EMAIL_TO_THE_CASE)
        action.soar_action.session = gmail_sync_session
        action.run()

        assert len(gmail_script_session.request_history) == 4
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_attachment(gmail_script_session.request_history, start=2, stop=4)

        assert len(gmail_sync_session.request_history) == 0

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.output_message ==
            NO_ATTACHMENTS_SAVED.format(
                ACTION_CONFIG_WITH_ATTACHMENTS_FILTERED["Internet Message ID"],
            )
        )
        assert action_output.results.result_value is False
        assert "message_id" in action_output.results.json_output.json_result
        assert "mime_content" not in action_output.results.json_output.json_result

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_ATTACHMENTS
    )
    def test_with_attachments(
            self,
            google_gmail: GoogleGmail,
            gmail_sync_session: GoogleGmailSession,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_with_files"])
        google_gmail.set_attachments(MOCK_DATA["attachments"])
        action = SaveEmailToTheCase(script_name=Constants.SAVE_EMAIL_TO_THE_CASE)
        action.soar_action.session = gmail_sync_session
        action.run()

        assert len(gmail_script_session.request_history) == 4
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_attachment(gmail_script_session.request_history, start=2, stop=4)

        assert len(gmail_sync_session.request_history) == 2
        assert_all_add_evidence(gmail_sync_session.request_history)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.output_message ==
            SUCCESS_ATTACHMENTS.format(
                ACTION_CONFIG_WITH_ATTACHMENTS["Internet Message ID"],
                "invite.ics,invite.ics"
            )
        )
        assert action_output.results.result_value is True
        assert "message_id" in action_output.results.json_output.json_result
        assert "mime_content" not in action_output.results.json_output.json_result

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_ATTACHMENTS_AND_ENCODE
    )
    def test_with_attachments_and_encode(
            self,
            google_gmail: GoogleGmail,
            gmail_sync_session: GoogleGmailSession,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_with_files"])
        google_gmail.set_attachments(MOCK_DATA["attachments"])
        action = SaveEmailToTheCase(script_name=Constants.SAVE_EMAIL_TO_THE_CASE)
        action.soar_action.session = gmail_sync_session
        action.run()

        assert len(gmail_script_session.request_history) == 5
        assert_all_list_messages(gmail_script_session.request_history, stop=1)
        assert_all_get_message(gmail_script_session.request_history, start=1, stop=3)
        assert_all_get_attachment(gmail_script_session.request_history, start=3, stop=5)

        assert len(gmail_sync_session.request_history) == 2
        assert_all_add_evidence(gmail_sync_session.request_history)

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert (
            action_output.results.output_message ==
            SUCCESS_ATTACHMENTS.format(
                ACTION_CONFIG_WITH_ATTACHMENTS_AND_ENCODE["Internet Message ID"],
                "invite.ics,invite.ics"
            )
        )
        assert action_output.results.result_value is True
        assert "message_id" in action_output.results.json_output.json_result
        assert "mime_content" in action_output.results.json_output.json_result
