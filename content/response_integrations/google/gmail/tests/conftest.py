from __future__ import annotations
pytest_plugins = ("integration_testing.conftest",)
import sys
import os
import pkgutil
import importlib
import soar_sdk
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f'soar_sdk.{name}'] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

import pathlib

import aiohttp
import google.auth.transport._aiohttp_requests
import pytest
import requests

from TIPCommon.types import SingleJson

from gmail.core.GoogleGmailAuth import GoogleGmailAuthManager
from gmail.core.GoogleGmailApiManager import GoogleGmailApiManager
from gmail.tests.core.async_session import GoogleGmailAsyncSession
from gmail.tests.core.google_gmail import GoogleGmail
from gmail.tests.core.session import GoogleGmailSession
from integration_testing.common import get_def_file_content, use_live_api


CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


@pytest.fixture
def google_gmail() -> GoogleGmail:
    yield GoogleGmail()


# pylint: disable=redefined-outer-name
@pytest.fixture(autouse=True)
def gmail_script_session(
    mocker,
    monkeypatch: pytest.MonkeyPatch,
    google_gmail: GoogleGmail,
) -> GoogleGmailSession:
    """Mock Google Gmail session and get back an object to view request history"""
    client_session = (
        GoogleGmailAsyncSession(mock_product=google_gmail, auto_decompress=False)
    )
    client_session._auth_request = mocker.AsyncMock()

    def __get_client_session(*_, **kwargs) -> GoogleGmailAsyncSession:
        if "credentials" in kwargs:
            client_session.credentials = kwargs["credentials"]
        return client_session

    if not use_live_api():
        monkeypatch.setattr(
            aiohttp,
            "ClientSession",
            __get_client_session
        )
        monkeypatch.setattr(
            google.auth.transport._aiohttp_requests.AuthorizedSession,
            "__new__",
            __get_client_session
        )

    yield client_session


# pylint: disable=redefined-outer-name
@pytest.fixture(autouse=True)
def gmail_sync_session(
    monkeypatch: pytest.MonkeyPatch,
    google_gmail: GoogleGmail,
) -> GoogleGmailSession:
    """Mock Google Gmail sync session and get back an object to view request history"""
    session: GoogleGmailSession = (
        GoogleGmailSession(mock_product=google_gmail)
    )
    if not use_live_api():
        monkeypatch.setattr(
            requests,
            "Session",
            lambda: session
        )

    yield session


@pytest.fixture
def google_gmail_api_manager() -> GoogleGmailApiManager:
    """GoogleGmailApiManager manager"""
    verify_ssl: bool = CONFIG["Verify SSL"]
    workload_identity_email = CONFIG["Workload Identity Email"]
    service_account_json = CONFIG["User Service Account JSON Secret"]
    user_email_address = CONFIG["Default Mailbox"]

    auth_manager = GoogleGmailAuthManager(
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
        delegated_email=user_email_address,
        verify_ssl=verify_ssl
    )
    auth_session = auth_manager.prepare_session()
    return GoogleGmailApiManager(auth_session)

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
