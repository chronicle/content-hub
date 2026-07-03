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

from ...actions.AddEmailLabel import (
    AddEmailLabel,
    EMPTY_PARAMS_MESSAGE,
    NO_MESSAGES_UPDATED_MESSAGE,
    SUCCESS_MESSAGE,
)
import gmail.core.GoogleGmailConsts as Constants

from ...tests.common import CONFIG, MOCK_DATA
from ...tests.core.async_session import GoogleGmailAsyncSession
from ...tests.core.google_gmail import GoogleGmail
from ...tests.utils import (
    assert_batch_modify,
    assert_create_label,
    assert_all_list_messages,
    assert_list_labels,
)
from integration_testing.common import get_def_file_content
from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata


ERROR = (
    f"Error executing action \"{Constants.ADD_EMAIL_LABEL_SCRIPT_NAME}\"\nReason:"
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

ACTION_CONFIG_WITH_INVALID_LABEL = ACTION_CONFIG_WITH_MAILBOXES.copy()
ACTION_CONFIG_WITH_INVALID_LABEL["Label"] = "invalid"

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
        action = AddEmailLabel(script_name=Constants.ADD_EMAIL_LABEL_SCRIPT_NAME)
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
        action = AddEmailLabel(script_name=Constants.ADD_EMAIL_LABEL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 2
        assert_list_labels(gmail_script_session.request_history)
        assert_all_list_messages(gmail_script_session.request_history, start=1)

        assert action_output.results == ActionOutput(
            output_message=(
                f"{ERROR} {NO_MESSAGES_UPDATED_MESSAGE.format('test@domain.com')}"
            ),
            result_value=False,
            execution_state=ExecutionState.FAILED,
            json_output=None,
        )

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MESSAGE_ID
    )
    def test_invalid_message_id(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        action = AddEmailLabel(script_name=Constants.ADD_EMAIL_LABEL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 2
        assert_list_labels(gmail_script_session.request_history)
        assert_all_list_messages(gmail_script_session.request_history, start=1)

        assert action_output.results == ActionOutput(
            output_message=(
                f"{ERROR} {NO_MESSAGES_UPDATED_MESSAGE.format('test@mailbox.com')}"
            ),
            result_value=False,
            execution_state=ExecutionState.FAILED,
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

        action = AddEmailLabel(script_name=Constants.ADD_EMAIL_LABEL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_list_labels(gmail_script_session.request_history)
        assert_all_list_messages(gmail_script_session.request_history, start=1, stop=2)
        assert_batch_modify(gmail_script_session.request_history, 2)

        assert action_output.results.output_message == (
            SUCCESS_MESSAGE.format(1, "test@mailbox.com")
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED


class TestFilter:
    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_MAILBOXES
    )
    def test_search_message_default_filter(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])

        action = AddEmailLabel(script_name=Constants.ADD_EMAIL_LABEL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_list_labels(gmail_script_session.request_history)
        assert_all_list_messages(gmail_script_session.request_history, start=1, stop=2)
        assert_batch_modify(gmail_script_session.request_history, 2)

        assert action_output.results.output_message == (
            SUCCESS_MESSAGE.format(2, "test@mailbox.com")
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_EMPTY_FILTER
    )
    def test_search_message_empty_filter(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])

        action = AddEmailLabel(script_name=Constants.ADD_EMAIL_LABEL_SCRIPT_NAME)
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

        action = AddEmailLabel(script_name=Constants.ADD_EMAIL_LABEL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 3
        assert_list_labels(gmail_script_session.request_history)
        assert_all_list_messages(gmail_script_session.request_history, start=1, stop=2)
        assert_batch_modify(gmail_script_session.request_history, 2)

        assert action_output.results.output_message == (
            SUCCESS_MESSAGE.format(1, "test@mailbox.com")
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        integration_config=CONFIG,
        parameters=ACTION_CONFIG_WITH_INVALID_LABEL
    )
    def test_invalid_label(
            self,
            google_gmail: GoogleGmail,
            gmail_script_session: GoogleGmailAsyncSession,
            action_output: MockActionOutput
    ) -> None:
        google_gmail.set_messages(MOCK_DATA["mail_without_attachments"])

        action = AddEmailLabel(script_name=Constants.ADD_EMAIL_LABEL_SCRIPT_NAME)
        action.run()

        assert len(gmail_script_session.request_history) == 4
        assert_list_labels(gmail_script_session.request_history)
        assert_create_label(gmail_script_session.request_history, 1)
        assert_all_list_messages(gmail_script_session.request_history, start=2, stop=3)
        assert_batch_modify(gmail_script_session.request_history, 3)

        assert action_output.results.output_message == (
            SUCCESS_MESSAGE.format(2, "test@mailbox.com")
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state == ExecutionState.COMPLETED
