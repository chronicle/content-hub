from __future__ import annotations

import copy
import pathlib
import sys

import requests
from Integrations.MicrosoftGraphMailDelegated.Managers import (
    exceptions,
    MicrosoftGraphMailDelegatedManager as api_manager,
)

from olefile.olefile import OleFileError

from TIPCommon.data_models import DatabaseContextType
from TIPCommon.types import SingleJson
from TIPCommon.utils import is_test_run

from Integrations.MicrosoftGraphMailDelegated.ConnectorsScripts import (
    MicrosoftGraphMailDelegatedConnector,
)
from Integrations.MicrosoftGraphMailDelegated.Managers.datamodels import (
    MicrosoftGraphAttachment,
    MicrosoftGraphEmail,
)
from Tests.integrations.MicrosoftGraphMailDelegated.core.session import MsGraphSession
from Tests.integrations.MicrosoftGraphMailDelegated.common import (
    CONFIG,
    DEFAULT_ATTACHMENT,
    DEFAULT_EMAIL,
    DEFAULT_FOLDER,
    USER_JSON,
    INTEGRATION_PATH,
    EMAIL_JSON,
)
from Tests.integrations.MicrosoftGraphMail.core.product import MicrosoftGraphMail
from Tests.mocks.common import set_is_test_run_to
from Tests.mocks.platform.script_output import MockConnectorOutput
from Tests.mocks.set_meta import set_metadata
from Tests.mocks.platform.external_context import (
    ExternalContextRowKey,
    MockExternalContext,
)

IDS_DB_KEY: str = "offset"
DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH
    / "Connectors"
    / "MicrosoftGraphMailDelegatedConnector.connectordef"
)

DEFAULT_PARAMETERS: SingleJson = {
    "Environment": "Default Environment",
    "Run Every": 10,
    "DeviceProductField": "device_product",
    "EventClassId": "event_name",
    "Microsoft Entra ID Endpoint": "https://login.microsoftonline.com",
    "Microsoft Graph Endpoint": "https://graph.microsoft.com",
    "Refresh Token": CONFIG.get("Refresh Token"),
    "Client ID": CONFIG.get("Client ID"),
    "Client Secret Value": CONFIG.get("Client Secret Value"),
    "Microsoft Entra ID Directory ID": CONFIG.get("Microsoft Entra ID Directory ID"),
    "Mail Address": CONFIG.get("User Mailbox"),
    "Mail Field Source": "false",
    "Offset Time In Hours": 24,
    "Max Emails Per Cycle": 10,
    "Unread Emails Only": "false",
    "Mark Emails as Read": "false",
    "Disable Overflow": "false",
    "Create a Separate Google SecOps Alert Per Attached Mail File": "false",
    "Folder To Check For Emails": "Inbox",
    "Verify SSL": "false",
}
ALERT_NAME: str = (
    f'Microsoft Graph Monitored Mailbox <{USER_JSON.get("userPrincipalName")}>'
)


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_microsoft_graph_mail_connector(
    ms_graph_mail: MicrosoftGraphMail,
    script_session: MsGraphSession,
    connector_output: MockConnectorOutput,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_attachment(DEFAULT_ATTACHMENT)

    set_is_test_run_to(True)
    is_test = is_test_run(sys.argv)
    connector = (
        MicrosoftGraphMailDelegatedConnector.MicrosoftGraphMailDelegatedConnector(
            is_test
        )
    )
    connector.start()

    assert len(script_session.request_history) == 7
    assert connector_output.results.json_output.alerts[0].name == ALERT_NAME


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_microsoft_graph_mail_connector_with_no_external_context(
    ms_graph_mail: MicrosoftGraphMail,
    script_session: MsGraphSession,
    connector_output: MockConnectorOutput,
    external_context: MockExternalContext,
) -> None:
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)
    ms_graph_mail.add_email(DEFAULT_EMAIL)
    ms_graph_mail.add_attachment(DEFAULT_ATTACHMENT)

    set_is_test_run_to(True)
    is_test = is_test_run(sys.argv)
    connector = (
        MicrosoftGraphMailDelegatedConnector.MicrosoftGraphMailDelegatedConnector(
            is_test
        )
    )
    connector.start()

    assert len(script_session.request_history) == 7
    assert connector_output.results.json_output.alerts[0].name == ALERT_NAME
    assert len(connector_output.results.json_output.alerts) == 1

    row_key: ExternalContextRowKey = ExternalContextRowKey(
        context_type=DatabaseContextType.CONNECTOR,
        property_key=IDS_DB_KEY,
        identifier=None,
    )
    assert row_key not in external_context


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_microsoft_graph_mail_delegated_connector_handle_msg_ole_error(
    ms_graph_mail: MicrosoftGraphMail,
    script_session: MsGraphSession,
    connector_output: MockConnectorOutput,
    mocker,
) -> None:
    """
    Test that the connector handles OLE Sector Error in MSG attachments gracefully.
    """
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    custom_attachment = {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "id": "mock_msg_id",
        "name": "test.msg",
        "contentType": "application/vnd.ms-outlook",
        "contentBytes": "SGVsbG8gV29ybGQ=",
        "size": 11
    }
    msg_attachment = MicrosoftGraphAttachment(
        raw_data=custom_attachment,
        **custom_attachment
    )
    msg_attachment.content = b"Hello World"

    ms_graph_mail.add_attachment(msg_attachment)

    my_email = MicrosoftGraphEmail(
        raw_data=copy.deepcopy(EMAIL_JSON),
        mailbox_name=CONFIG.get("User Mailbox"),
        folder_name="Inbox",
        mail_id=EMAIL_JSON.get("id"),
        **EMAIL_JSON,
    )
    my_email.set_attachments([msg_attachment])
    ms_graph_mail.add_email(my_email)

    mocker.patch(
        "EmailUtils.extract_msg.Message",
        side_effect=OleFileError("incorrect OLE sector index for empty stream"),
    )

    set_is_test_run_to(True)
    is_test = is_test_run(sys.argv)
    connector = (
        MicrosoftGraphMailDelegatedConnector.MicrosoftGraphMailDelegatedConnector(
            is_test
        )
    )
    spy_attach = mocker.spy(connector, "_attach_file_to_case")
    connector.start()

    # Verify that the corrupted MSG was added as a regular attachment
    assert spy_attach.call_count == 1
    assert spy_attach.call_args[0][0] == "test.msg"
    assert len(script_session.request_history) == 7
    assert len(connector_output.results.json_output.alerts) == 1
    assert connector_output.results.json_output.alerts[0].name == ALERT_NAME


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_microsoft_graph_mail_delegated_connector_with_msg_success(
    ms_graph_mail: MicrosoftGraphMail,
    script_session: MsGraphSession,
    connector_output: MockConnectorOutput,
    mocker,
) -> None:
    """
    Test that the connector successfully parses a valid MSG attachment.
    """
    ms_graph_mail.add_user(USER_JSON)
    ms_graph_mail.add_folder(DEFAULT_FOLDER)

    custom_attachment = {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "id": "mock_msg_id",
        "name": "test.msg",
        "contentType": "application/vnd.ms-outlook",
        "contentBytes": "SGVsbG8gV29ybGQ=",
        "size": 11
    }
    msg_attachment = MicrosoftGraphAttachment(
        raw_data=custom_attachment,
        **custom_attachment
    )
    msg_attachment.content = b"Hello World"

    ms_graph_mail.add_attachment(msg_attachment)

    my_email = MicrosoftGraphEmail(
        raw_data=copy.deepcopy(EMAIL_JSON),
        mailbox_name=CONFIG.get("User Mailbox"),
        folder_name="Inbox",
        mail_id=EMAIL_JSON.get("id"),
        **EMAIL_JSON,
    )
    my_email.set_attachments([msg_attachment])
    ms_graph_mail.add_email(my_email)

    mock_msg = mocker.Mock()
    mock_msg.attachments = []
    mock_msg.header = mocker.Mock()
    mock_msg.header.keys.return_value = []
    mocker.patch(
        "EmailUtils.extract_msg.Message",
        return_value=mock_msg,
    )

    mock_siemplify_mail = {
        "answer": "Test Answer",
        "attachments": [],
        "unixTimeDate": 1704103200000,
        "date": "2024-01-01T10:00:00Z",
    }
    mocker.patch.object(
        MicrosoftGraphMailDelegatedConnector.EmailUtils,
        "convert_outlook_msg_to_siemplify_msg",
        return_value=mock_siemplify_mail,
    )

    set_is_test_run_to(True)
    is_test = is_test_run(sys.argv)
    connector = (
        MicrosoftGraphMailDelegatedConnector.MicrosoftGraphMailDelegatedConnector(
            is_test
        )
    )
    connector.start()

    assert len(script_session.request_history) == 7
    assert len(connector_output.results.json_output.alerts) == 1
    assert connector_output.results.json_output.alerts[0].name == ALERT_NAME


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_connector_manager_error_handled_gracefully(
    connector_output: MockConnectorOutput,
    mocker,
) -> None:
    """MicrosoftGraphMailManagerError is caught gracefully and returns empty list."""
    set_is_test_run_to(False)
    is_test: bool = is_test_run(sys.argv)
    mocker.patch.object(
        api_manager.ApiManager,
        "get_emails",
        side_effect=exceptions.MicrosoftGraphMailManagerError("502 Bad Gateway"),
    )

    connector = (
        MicrosoftGraphMailDelegatedConnector.MicrosoftGraphMailDelegatedConnector(
            is_test
        )
    )
    connector.start()

    assert connector_output.results.json_output.alerts == []


@set_metadata(connector_def_file_path=DEF_PATH, parameters=DEFAULT_PARAMETERS)
def test_connector_request_exception_handled_gracefully(
    connector_output: MockConnectorOutput,
    mocker,
) -> None:
    """RequestException is caught gracefully and returns empty list."""
    set_is_test_run_to(False)
    is_test: bool = is_test_run(sys.argv)

    mocker.patch.object(
        api_manager.ApiManager,
        "get_emails",
        side_effect=requests.exceptions.RequestException("Connection timeout"),
    )

    connector = (
        MicrosoftGraphMailDelegatedConnector.MicrosoftGraphMailDelegatedConnector(
            is_test
        )
    )
    connector.start()

    assert connector_output.results.json_output.alerts == []
