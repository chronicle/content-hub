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

import asyncio
import pathlib
import json

import pytest

from TIPCommon.data_models import DatabaseContextType
from TIPCommon.types import SingleJson
from TIPCommon.consts import IDS_DB_KEY

from gmail.connectors.GmailConnector import main
from gmail.tests.common import INTEGRATION_PATH, MOCK_DATA
from gmail.tests.core.async_session import GoogleGmailAsyncSession
from gmail.tests.core.google_gmail import GoogleGmail
from gmail.tests.utils import (
    assert_all_list_messages,
    assert_all_get_message,
    assert_all_get_attachment,
    assert_list_labels,
)
from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.external_context import ExternalContextRowKey
from integration_testing.platform.external_context import MockExternalContext
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata


DEF_PATH: pathlib.Path = pathlib.Path(__file__).parent / "mock_gmail_connector.json"
DEFAULT_PARAMETERS: SingleJson = {
    "DeviceProductField": "alert_type",
    "EventClassId": "event_type",
    "Workload Identity Email": "gmail@test-project.iam.gserviceaccount.com",
    "User Service Account JSON Secret": None,
    "Max Emails Per Cycle": 10,
    "Max Hours Backwards": 1,
    "Default Mailbox": "test@domain.com",
    "Email Status": "Both",
    "Verify SSL": True,
    "Labels Filter": "",
    "Extract Headers": "",
    "Email Exclude Pattern": "",
    "Attach Original EML": False,
    "Original Mail File Prefix": "Original_Mail",
    "Attached Mail File Prefix": "Attached_Mail",
    "Case Name Template": "",
    "Alert Name Template": "",
    "Create Alert Per Attachment File": False,
    "Disable Overflow": False,
    "PythonProcessTimeout": 180,
    "Environment Field Name": "",
    "Environment Regex Pattern": ".*"
}
PARAMETERS_WITH_MULTIPLE_ALERTS_MODE: SingleJson = DEFAULT_PARAMETERS.copy()
PARAMETERS_WITH_MULTIPLE_ALERTS_MODE["Create Alert Per Attachment File"] = True
PARAMETERS_ATTACH_EML: SingleJson = DEFAULT_PARAMETERS.copy()
PARAMETERS_ATTACH_EML["Attach Original EML"] = True


class TestTestRun:
    @set_metadata(
            connector_def_file_path=DEF_PATH,
            parameters=DEFAULT_PARAMETERS
    )
    def test_connector_test_run_no_mail(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            connector_output: MockConnectorOutput,
    ) -> None:
        set_is_test_run_to_true()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

        assert connector_output.results.json_output.alerts == []
        assert len(gmail_script_session.request_history) == 2
        assert_list_labels(gmail_script_session.request_history, index=1)
        assert_all_list_messages(gmail_script_session.request_history, start=1)

    @set_metadata(
            connector_def_file_path=DEF_PATH,
            parameters=DEFAULT_PARAMETERS,
    )
    def test_connector_test_run_with_mail(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            connector_output: MockConnectorOutput,
            google_gmail: GoogleGmail,
    ) -> None:
        google_gmail.set_messages(
            MOCK_DATA["mail_without_attachments"],
            set_ts_to_now=True
        )
        set_is_test_run_to_true()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

        assert_list_labels(gmail_script_session.request_history, index=1)
        assert_all_list_messages(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2)
        assert len(connector_output.results.json_output.alerts) == 1

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_mail_no_context(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            connector_output: MockConnectorOutput,
            google_gmail: GoogleGmail,
            external_context: MockExternalContext,
    ) -> None:
        google_gmail.set_messages(
            MOCK_DATA["mail_without_attachments"],
            set_ts_to_now=True
        )
        set_is_test_run_to_true()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

        assert_list_labels(gmail_script_session.request_history, index=1)
        assert_all_list_messages(gmail_script_session.request_history, stop=2, start=1)
        assert_all_get_message(gmail_script_session.request_history, start=2)
        assert len(connector_output.results.json_output.alerts) == 1

        row_key: ExternalContextRowKey = ExternalContextRowKey(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert row_key not in external_context


class TestConnectorExternalContext:

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_mail_ids(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            connector_output: MockConnectorOutput,
            google_gmail: GoogleGmail,
            external_context: MockExternalContext,
    ) -> None:
        google_gmail.set_messages(
            MOCK_DATA["mail_without_attachments"],
            set_ts_to_now=True
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

        assert_list_labels(gmail_script_session.request_history, index=1)
        assert_all_list_messages(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2)
        assert len(connector_output.results.json_output.alerts) == 2

        ids_json = external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert ids_json

        ids: list[str] = json.loads(ids_json)
        assert len(ids) == 2

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_mail_timestamp(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            connector_output: MockConnectorOutput,
            google_gmail: GoogleGmail,
            external_context: MockExternalContext,
    ) -> None:
        google_gmail.set_messages(
            MOCK_DATA["mail_without_attachments"],
            set_ts_to_now=True
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

        assert_list_labels(gmail_script_session.request_history, index=1)
        assert_all_list_messages(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2)
        assert len(connector_output.results.json_output.alerts) == 2

        timestamp_str = external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key="timestamp",
            identifier=None,
        )
        assert (
            timestamp_str
            == sorted(
                google_gmail.messages.values(),
                key=lambda m: m["internalDate"],
                reverse=True
            )[0]["internalDate"]
        )


class TestConnectorWithAttachments:
    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=PARAMETERS_ATTACH_EML,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_attach_eml(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            connector_output: MockConnectorOutput,
            google_gmail: GoogleGmail,
            external_context: MockExternalContext,
    ) -> None:
        google_gmail.set_messages(
            MOCK_DATA["mail_without_attachments"],
            set_ts_to_now=True
        )

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

        assert_list_labels(gmail_script_session.request_history, index=1)
        assert_all_list_messages(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2)
        assert len(connector_output.results.json_output.alerts) == 2
        assert all(
            alert.attachments[0]["type"] == ".eml"
            for alert in connector_output.results.json_output.alerts
        )

        ids_json = external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert ids_json

        ids: list[str] = json.loads(ids_json)
        assert len(ids) == 2

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_eml_single_alert(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            connector_output: MockConnectorOutput,
            google_gmail: GoogleGmail,
            external_context: MockExternalContext,
    ) -> None:
        google_gmail.set_messages(
            MOCK_DATA["mail_with_eml"],
            set_ts_to_now=True
        )
        google_gmail.set_attachments(MOCK_DATA["attachments"])

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

        assert_list_labels(gmail_script_session.request_history, index=1)
        assert_all_list_messages(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2, stop=3)
        assert_all_get_attachment(gmail_script_session.request_history, start=3)
        assert len(connector_output.results.json_output.alerts) == 1
        assert all(
            alert.attachments
            for alert in connector_output.results.json_output.alerts
        )

        ids_json = external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert ids_json

        ids: list[str] = json.loads(ids_json)
        assert len(ids) == 1

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=PARAMETERS_WITH_MULTIPLE_ALERTS_MODE,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_eml_multiple_alerts(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            connector_output: MockConnectorOutput,
            google_gmail: GoogleGmail,
            external_context: MockExternalContext,
    ) -> None:
        google_gmail.set_messages(
            MOCK_DATA["mail_with_eml"],
            set_ts_to_now=True
        )
        google_gmail.set_attachments(MOCK_DATA["attachments"])

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

        assert_list_labels(gmail_script_session.request_history, index=1)
        assert_all_list_messages(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2, stop=3)
        assert_all_get_attachment(gmail_script_session.request_history, start=3)
        assert len(connector_output.results.json_output.alerts) == 2
        assert all(
            not alert.attachments
            for alert in connector_output.results.json_output.alerts[:-1]
        )
        assert connector_output.results.json_output.alerts[-1].attachments

        ids_json = external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert ids_json

        ids: list[str] = json.loads(ids_json)
        assert len(ids) == 1

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=PARAMETERS_WITH_MULTIPLE_ALERTS_MODE,
        external_context=MockExternalContext(),
    )
    def test_connector_test_run_with_attachments(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            connector_output: MockConnectorOutput,
            google_gmail: GoogleGmail,
            external_context: MockExternalContext,
    ) -> None:
        google_gmail.set_messages(
            MOCK_DATA["mail_with_files"],
            set_ts_to_now=True
        )
        google_gmail.set_attachments(MOCK_DATA["attachments"])

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

        assert_list_labels(gmail_script_session.request_history, index=1)
        assert_all_list_messages(gmail_script_session.request_history, start=1, stop=2)
        assert_all_get_message(gmail_script_session.request_history, start=2, stop=3)
        assert_all_get_attachment(gmail_script_session.request_history, start=3)
        assert len(connector_output.results.json_output.alerts) == 1
        assert all(
            alert.attachments
            for alert in connector_output.results.json_output.alerts
        )

        ids_json = external_context.get_row_value(
            context_type=DatabaseContextType.CONNECTOR,
            property_key=IDS_DB_KEY,
            identifier=None,
        )
        assert ids_json

        ids: list[str] = json.loads(ids_json)
        assert len(ids) == 1


@pytest.mark.usefixtures("gmail_script_session")
class TestConnectorApiError:
    """Tests covering the connector API/auth failure path."""

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=DEFAULT_PARAMETERS,
    )
    def test_connector_api_error(
            self,
            google_gmail: GoogleGmail,
            mocker,
    ) -> None:
        """Connector propagates an API error raised during get_alerts.

        When the Gmail labels API call fails (e.g. due to an auth or network
        issue), the exception must propagate to the caller in test-run mode.
        """
        set_is_test_run_to_true()

        # ISSUE FINDER: list_labels is called inside get_alerts (not init_managers),
        # so the exception is caught by the outer handler and re-raised only in
        # test-run mode. In a production run the error would be silently logged.
        mocker.patch.object(
            google_gmail,
            "list_labels",
            side_effect=Exception("Simulated API error"),
        )

        loop = asyncio.get_event_loop()
        with pytest.raises(Exception, match="Simulated API error"):
            loop.run_until_complete(main())


UNREAD_ONLY_PARAMETERS: SingleJson = DEFAULT_PARAMETERS.copy()
UNREAD_ONLY_PARAMETERS["Email Status"] = "Unread"


class TestEmailStatusFilter:
    """Tests covering email status filtering."""

    @set_metadata(
        connector_def_file_path=DEF_PATH,
        parameters=UNREAD_ONLY_PARAMETERS,
    )
    def test_connector_unread_filter(
            self,
            gmail_script_session: GoogleGmailAsyncSession,
            connector_output: MockConnectorOutput,
            google_gmail: GoogleGmail,
    ) -> None:
        """Connector with Email Status=Unread runs successfully.

        Verifies the connector processes emails correctly when the
        Unread-only filter is enabled.
        """
        google_gmail.set_messages(
            MOCK_DATA["mail_without_attachments"],
            set_ts_to_now=True,
        )
        set_is_test_run_to_true()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())

        assert_list_labels(gmail_script_session.request_history, index=1)
        assert len(connector_output.results.json_output.alerts) == 1
