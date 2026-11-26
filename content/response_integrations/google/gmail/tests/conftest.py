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
from typing import TYPE_CHECKING, Any, SupportsIndex
from urllib.parse import parse_qs

import aiohttp
import google.auth
import google.auth.compute_engine
import google.auth.transport._aiohttp_requests
import pytest
import requests
import soar_sdk  # noqa: F401
import integration_testing.common as integration_testing_common
import integration_testing.set_meta as integration_testing_set_meta
from integration_testing.aiohttp.session import HistoryRecord, HistoryRecordsList
from integration_testing.common import get_def_file_content, use_live_api
from integration_testing.request import MockRequest

import gmail.core.GoogleGmailApiManager
from gmail.core.GoogleGmailApiManager import GoogleGmailApiManager
from gmail.core.GoogleGmailAuth import GoogleGmailAuthManager
from gmail.tests.core.async_session import GoogleGmailAsyncSession
from gmail.tests.core.google_gmail import GoogleGmail
from gmail.tests.core.session import GoogleGmailSession

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest_mock import MockerFixture
    from TIPCommon.types import SingleJson

pytest_plugins = ("integration_testing.conftest",)

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)

YAML_PARAM_TYPE_MAP: dict[str, int] = {
    "boolean": 0,
    "integer": 1,
    "int": 1,
    "string": 2,
    "password": 3,
    "ip": 4,
    "host": 5,
    "url": 6,
    "domain": 7,
    "email": 8,
}


def _history_getitem(
    self: HistoryRecordsList,
    item: int | slice | SupportsIndex,
) -> HistoryRecordsList | HistoryRecord:
    """Fix UserList slice unpacking bug in integration_testing HistoryRecordsList."""
    if isinstance(item, slice):
        return HistoryRecordsList(*self.data[item])
    return self.data[item]


HistoryRecordsList.__getitem__ = _history_getitem  # type: ignore[method-assign]


def _mock_request_params(request: MockRequest) -> dict[str, list[str]]:
    """Backport MockRequest.params for integration_testing 2.2.18."""
    params = parse_qs(request.url.query)
    raw_params = request.kwargs.get("params")
    if isinstance(raw_params, dict):
        for key, value in raw_params.items():
            if key not in params:
                params[key] = [str(value)]
    return params


if not hasattr(MockRequest, "params"):
    MockRequest.params = property(_mock_request_params)  # type: ignore[attr-defined]


def _install_html2text_links_shim() -> None:
    """Populate legacy siemplify_html2text link attributes when standard html2text is installed."""
    import html2text
    from bs4 import BeautifulSoup

    if hasattr(html2text.HTML2Text(), "html_links"):
        return

    orig_handle = html2text.HTML2Text.handle

    def _patched_handle(self: html2text.HTML2Text, data: str) -> str:
        result = orig_handle(self, data)
        soup = BeautifulSoup(data, "html.parser")
        html_links: list[str] = []
        html_links_original_src: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = anchor.get("href")
            if href is None:
                continue
            text = anchor.get_text().replace("\xa0", "")
            if text != href:
                html_links.append(text)
            if original_src := anchor.get("originalsrc"):
                html_links_original_src.append(str(original_src))
        self.html_links = html_links  # type: ignore[attr-defined]
        self.html_links_original_src = html_links_original_src  # type: ignore[attr-defined]
        return result

    html2text.HTML2Text.handle = _patched_handle  # type: ignore[method-assign]


_install_html2text_links_shim()


@pytest.fixture
def google_gmail() -> Iterator[GoogleGmail]:
    """Return mock Gmail product state."""
    yield GoogleGmail()


@pytest.fixture(autouse=True)
def gmail_script_session(
    mocker: MockerFixture,
    monkeypatch: pytest.MonkeyPatch,
    google_gmail: GoogleGmail,
) -> Iterator[GoogleGmailAsyncSession]:
    """Mock Google Gmail async session and normalize YAML connector definitions."""
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    client_session = GoogleGmailAsyncSession(
        mock_product=google_gmail, auto_decompress=False
    )
    client_session._auth_request = mocker.AsyncMock()

    original_get_def = integration_testing_common.get_def_file_content

    def normalized_get_def_file_content(
        def_file_path: pathlib.Path,
    ) -> dict[str, Any]:
        data = original_get_def(def_file_path)
        if (
            isinstance(data, dict)
            and "Parameters" not in data
            and isinstance(data.get("parameters"), list)
        ):
            data["Parameters"] = [
                {
                    "Name": param["name"],
                    "Type": YAML_PARAM_TYPE_MAP.get(
                        str(param.get("type", "string")).lower(), 2
                    ),
                    "DefaultValue": param.get("default_value", ""),
                    "IsMandatory": param.get("is_mandatory", False),
                    "Mode": 2 if param.get("mode") == "script" else 0,
                }
                for param in data["parameters"]
            ]
        return data

    monkeypatch.setattr(
        integration_testing_common,
        "get_def_file_content",
        normalized_get_def_file_content,
    )
    if hasattr(integration_testing_set_meta, "get_def_file_content"):
        monkeypatch.setattr(
            integration_testing_set_meta,
            "get_def_file_content",
            normalized_get_def_file_content,
        )

    def _get_client_session(*_: Any, **kwargs: Any) -> GoogleGmailAsyncSession:
        if "credentials" in kwargs:
            client_session.credentials = kwargs["credentials"]
        return client_session

    if not use_live_api():
        monkeypatch.setenv(
            "GOOGLE_API_PREVENT_AGENT_TOKEN_SHARING_FOR_GCP_SERVICES", "false"
        )
        monkeypatch.setattr(aiohttp, "ClientSession", _get_client_session)
        monkeypatch.setattr(
            google.auth.transport._aiohttp_requests.AuthorizedSession,
            "__new__",
            _get_client_session,
        )
        monkeypatch.setattr(
            google.auth,
            "default",
            lambda *_args, **_kwargs: (
                google.auth.compute_engine.Credentials(
                    universe_domain="googleapis.com"
                ),
                "mock-project",
            ),
        )
        monkeypatch.setattr(
            gmail.core.GoogleGmailApiManager,
            "get_workload_sa_email",
            lambda default_sa_to_return="Unknown Principal": default_sa_to_return,
        )

    yield client_session


@pytest.fixture(autouse=True)
def gmail_sync_session(
    monkeypatch: pytest.MonkeyPatch,
    google_gmail: GoogleGmail,
) -> Iterator[GoogleGmailSession]:
    """Mock Google Gmail sync session for GCE metadata and SOAR SDK requests."""
    session = GoogleGmailSession(mock_product=google_gmail)
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)

    yield session


@pytest.fixture
def google_gmail_api_manager() -> GoogleGmailApiManager:
    """Return configured GoogleGmailApiManager instance for unit tests."""
    verify_ssl: bool = CONFIG["Verify SSL"]
    workload_identity_email = CONFIG["Workload Identity Email"]
    service_account_json = CONFIG["User Service Account JSON Secret"]
    user_email_address = CONFIG["Default Mailbox"]

    auth_manager = GoogleGmailAuthManager(
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
        delegated_email=user_email_address,
        verify_ssl=verify_ssl,
    )
    auth_session = auth_manager.prepare_session()
    return GoogleGmailApiManager(auth_session)
