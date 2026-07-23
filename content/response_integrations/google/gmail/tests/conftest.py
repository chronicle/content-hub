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

# Unify the soar_sdk namespace with the flat namespace for mocks
import sys
import pkgutil
import soar_sdk

import importlib
import pkgutil
import sys

# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon
sdk_dir = soar_sdk.__path__[0]
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

# Save original stdout in case soar_sdk imports hijack it (Siemplify.py calls SiemplifyUtils.override_stdout)
original_stdout = sys.stdout
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    try:
        flat_mod = importlib.import_module(name)
        sys.modules[f"soar_sdk.{name}"] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout
import importlib
            
# Mock is_overflow_alert for integration tests to prevent Container crash
import TIPCommon.base.connector
TIPCommon.base.connector.Connector.is_overflow_alert = lambda self, alert_info: False

import os
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

import unittest.mock
_mock_creds = unittest.mock.Mock()
_mock_creds.universe_domain = "googleapis.com"
_patcher1 = unittest.mock.patch("google.auth.default", return_value=(_mock_creds, "test-project"))
_patcher2 = unittest.mock.patch("TIPCommon.rest.auth.get_adc", return_value=(_mock_creds, "test-project"))
_patcher1.start()
_patcher2.start()


from integration_testing.aiohttp.session import HistoryRecordsList
_original_hrl_init = HistoryRecordsList.__init__
def _patched_hrl_init(self, *args):
    if len(args) == 1 and isinstance(args[0], list):
        args = tuple(args[0])
    _original_hrl_init(self, *args)
HistoryRecordsList.__init__ = _patched_hrl_init



import pytest
import requests

import soar_sdk

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

import aiohttp
import google.auth.transport._aiohttp_requests
from TIPCommon.types import SingleJson

from ..core.GoogleGmailAuth import GoogleGmailAuthManager
from ..core.GoogleGmailApiManager import GoogleGmailApiManager
from ..tests.core.async_session import GoogleGmailAsyncSession
from ..tests.core.google_gmail import GoogleGmail
from ..tests.core.session import GoogleGmailSession
from integration_testing.common import get_def_file_content, use_live_api

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


import html2text
original_html2text_init = html2text.HTML2Text.__init__
def _mock_html2text_init(self, *args, **kwargs):
    original_html2text_init(self, *args, **kwargs)
    self.html_links = []
    self.html_links_original_src = []
html2text.HTML2Text.__init__ = _mock_html2text_init

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
        GoogleGmailAsyncSession(mock_product=google_gmail, auto_decompress=False, loop=__import__('asyncio').new_event_loop())
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
            aiohttp,
            "TCPConnector",
            mocker.MagicMock()
        )
        monkeypatch.setattr(
            google.auth.transport._aiohttp_requests.AuthorizedSession,
            "__new__",
            __get_client_session
        )

    yield client_session
    
    # Suppress "Unclosed client session" warnings that pollute stdout and break JSON parsing
    if not client_session.closed:
        client_session._loop.run_until_complete(client_session.close())


# pylint: disable=redefined-outer-name
import pytest
import asyncio
from typing import Iterator

@pytest.fixture(autouse=True)
def ensure_event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Ensure there is a current event loop for synchronous tests."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    yield loop
    
    # We do not close it here to avoid breaking subsequent tests that might reuse it

from integration_testing.aiohttp.response import MockClientResponse

def patch_mock_client_response():
    original_init = MockClientResponse.__init__
    def new_init(self, *args, **kwargs):
        try:
            original_init(self, *args, **kwargs)
        except TypeError as e:
            if "stream_writer" in str(e):
                import aiohttp
                import asyncio
                import json
                from yarl import URL
                from TIPCommon.utils import none_to_default_value
                
                content = kwargs.get("content", "") if "content" in kwargs else (args[0] if len(args) > 0 else "")
                status_code = kwargs.get("status_code", 200) if "status_code" in kwargs else (args[1] if len(args) > 1 else 200)
                encoding = kwargs.get("encoding", "UTF-8") if "encoding" in kwargs else (args[2] if len(args) > 2 else "UTF-8")
                headers = kwargs.get("headers", None) if "headers" in kwargs else (args[3] if len(args) > 3 else None)
                method = kwargs.get("method", "") if "method" in kwargs else (args[4] if len(args) > 4 else "")
                url = kwargs.get("url", "") if "url" in kwargs else (args[5] if len(args) > 5 else "")
                
                class MockStreamWriter:
                    output_size = 0
                
                aiohttp.ClientResponse.__init__(
                    self,
                    method=method,
                    url=URL(url),
                    writer=None,
                    continue100=None,
                    timer=None,
                    request_info=None,
                    traces=None,
                    session=None,
                    loop=asyncio.get_event_loop(),
                    stream_writer=MockStreamWriter(),
                )
                self.content = aiohttp.streams.StreamReader(
                    aiohttp.base_protocol.BaseProtocol(asyncio.get_event_loop()),
                    2**32,
                )
                def _stringify_content(c):
                    if not isinstance(c, str):
                        return json.dumps(c)
                    return c
                self.content.feed_data(_stringify_content(content).encode(encoding))
                self.content.feed_eof()
                self.status = status_code
                self.encoding = encoding
                self._headers = none_to_default_value(headers, {})
                self._traces = []
                self.reason = "Some very valid reason"
            else:
                raise e
    MockClientResponse.__init__ = new_init

patch_mock_client_response()

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
        import typing
        def mock_session_request(self_obj: typing.Any, method: str, url: str, *args: typing.Any, **kwargs: typing.Any) -> MockResponse:
            return session.request(method, url, *args, **kwargs)

        def mock_get(url: str, *args: typing.Any, **kwargs: typing.Any) -> MockResponse:
            return session.request("GET", url, *args, **kwargs)
            
        def mock_post(url: str, *args: typing.Any, **kwargs: typing.Any) -> MockResponse:
            return session.request("POST", url, *args, **kwargs)

        monkeypatch.setattr(requests.sessions.Session, "request", mock_session_request)
        monkeypatch.setattr(requests, "get", mock_get)
        monkeypatch.setattr(requests, "post", mock_post)

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
    manager = GoogleGmailApiManager(auth_session)
    yield manager
    
    if hasattr(auth_session, 'close'):
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                pass # Just let it gc if running
            else:
                try:
                    loop.run_until_complete(auth_session.close())
                except Exception:
                    pass
        except RuntimeError:
            pass


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


# Prevent GoogleGmailBaseAction from bypassing the test framework's stdout capture
try:
    from ..core.GoogleGmailBaseAction import GoogleGmailBaseAction
    GoogleGmailBaseAction._fix_sdk_stdout = lambda self: None
except ImportError:
    pass



