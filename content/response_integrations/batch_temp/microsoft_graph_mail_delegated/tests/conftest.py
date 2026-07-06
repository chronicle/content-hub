from __future__ import annotations

from collections import namedtuple
import json
import os
import pytest
from pytest_mock import MockerFixture
from TIPCommon.base.utils import CreateSession

from SiemplifyBase import SiemplifyBase
from Integrations.MicrosoftGraphMailDelegated.Managers\
    .MicrosoftGraphMailDelegatedManager import ApiManager, ApiParameters
from Tests.integrations.MicrosoftGraphMailDelegated.common import CONFIG
from Tests.integrations.MicrosoftGraphMailDelegated.core.session import MsGraphSession
from Tests.integrations.MicrosoftGraphMailDelegated.core.product import (
    MicrosoftGraphMailDelegated,
)
from Tests.mocks.common import use_live_api
from Tests.mocks.logger import Logger

INTEGRATION_NAME = "MicrosoftGraphMailDelegated"
IntegrationParameters = namedtuple(
    "IntegrationParameters",
    [
        "azure_ad_endpoint",
        "microsoft_graph_endpoint",
        "client_id",
        "client_secret",
        "tenant",
        "refresh_token",
        "redirect_url",
        "mail_field_source",
        "user_mailbox",
        "verify_ssl",
    ],
)


def read_config() -> IntegrationParameters:
    """Read config.json to get the integration credentials.

    Returns:
        _type_: _description_
    """
    with open("config.json", encoding="UTF-8") as f:
        data = f.read()

    config = json.loads(data)
    azure_ad_endpoint = config.get("Microsoft Entra ID Endpoint")
    microsoft_graph_endpoint = config.get("Microsoft Graph Endpoint")
    client_id = config.get("Client ID")
    client_secret = config.get("Client Secret Value")
    tenant = config.get("Microsoft Entra ID Directory ID")
    refresh_token = config.get("Refresh Token")
    redirect_url = config.get("Redirect URL")
    mail_field_source = config.get("Mail Field Source")
    user_mailbox = config.get("User Mailbox")
    verify_ssl = config.get("Verify SSL")

    return IntegrationParameters(
        azure_ad_endpoint,
        microsoft_graph_endpoint,
        client_id,
        client_secret,
        tenant,
        refresh_token,
        redirect_url,
        mail_field_source,
        user_mailbox,
        verify_ssl,
    )


@pytest.fixture(scope="module")
def mock_data() -> dict:
    return json.load(
        open(
            os.path.join(os.path.dirname(__file__), "mock_data.json"),
            encoding="utf-8",
        )
    )


def get_api_parameters() -> ApiParameters:
    config = read_config()
    return ApiParameters(
        api_root=config.microsoft_graph_endpoint,
        client_id=config.client_id,
        client_secret=config.client_secret,
        tenant=config.tenant,
        mail_address=config.user_mailbox,
    )


@pytest.fixture(scope="module")
def ms_graph_mail_manager() -> ApiManager:
    """Get ApiManager instance for Unit Tests.

    Yields:
        ApiManager: ApiManager instance.
    """
    session = CreateSession.create_session()
    api_parameters = get_api_parameters()
    logger = MockerFixture(INTEGRATION_NAME).Mock()
    yield ApiManager(
        session=session,
        api_parameters=api_parameters,
        logger=logger,
    )


@pytest.fixture
def ms_graph_mail() -> MicrosoftGraphMailDelegated:
    yield MicrosoftGraphMailDelegated()


# pylint: disable=redefined-outer-name
@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    ms_graph_mail: MicrosoftGraphMailDelegated,
) -> MsGraphSession:
    """
    Mock MicrosoftGraphMailDelegated scripts' session and get back an object
    to view request history.
    """
    session: MsGraphSession = MsGraphSession(ms_graph_mail)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)

    yield session


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch) -> MsGraphSession:
    """Mock the SDK sessions and get it back to view request and response history"""
    session: MsGraphSession = MsGraphSession(ms_graph_mail)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

    yield session


@pytest.fixture
def ms_graph_manager(script_session: MsGraphSession) -> ApiManager:
    """MicrosoftGraphMailDelegated manager"""
    api_root: str = CONFIG["Microsoft Graph Endpoint"]
    client_id: str = CONFIG["Client ID"]
    client_secret: str = CONFIG["Client Secret Value"]
    tenant: str = CONFIG["Microsoft Entra ID Directory ID"]
    mail_address = CONFIG["User Mailbox"]
    logger = Logger()
    api_params: ApiParameters = ApiParameters(
        api_root,
        client_id,
        client_secret,
        tenant,
        mail_address,
    )

    yield ApiManager(script_session, api_params, logger)
