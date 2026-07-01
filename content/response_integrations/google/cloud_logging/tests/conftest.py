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

for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    if name not in sys.modules:
        try:
            sys.modules[name] = __import__(f"soar_sdk.{name}", fromlist=[None])
        except Exception:
            pass

import os
import sys
import pkgutil
import pathlib


import pytest
import requests

import soar_sdk

import TIPCommon.base.connector
TIPCommon.base.connector.Connector.is_overflow_alert = lambda self, alert_info: False

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)


import typing
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))

from integration_testing.requests.response import MockResponse
from integration_testing.request import MockRequest, HttpMethod
from ..tests.core.session import GoogleCloudApiSession
import urllib.parse

@pytest.fixture(name="gcloud_api_script_session", autouse=True)
def gcloud_api_script_session_fixture(monkeypatch: pytest.MonkeyPatch) -> GoogleCloudApiSession:
    session = GoogleCloudApiSession()

    def mock_session_request(self_obj: typing.Any, method: str, url: str, *args: typing.Any, **kwargs: typing.Any) -> MockResponse:
        return session.request(method, url, *args, **kwargs)

    def mock_get(url: str, *args: typing.Any, **kwargs: typing.Any) -> MockResponse:
        return session.request("GET", url, *args, **kwargs)
        
    def mock_post(url: str, *args: typing.Any, **kwargs: typing.Any) -> MockResponse:
        return session.request("POST", url, *args, **kwargs)

    monkeypatch.setattr(requests.sessions.Session, "request", mock_session_request)
    monkeypatch.setattr(requests, "get", mock_get)
    monkeypatch.setattr(requests, "post", mock_post)

    return session

from ..core.CloudLoggingApiManager import CloudLoggingApiManager, ApiManagerParams

@pytest.fixture(name="gcloud_api_manager", autouse=True)
def gcloud_api_manager_fixture(gcloud_api_script_session) -> CloudLoggingApiManager:
    params = ApiManagerParams(
        api_root="https://logging.googleapis.com",
        project_id="test-project",
        organization_id="12345"
    )
    return CloudLoggingApiManager(gcloud_api_script_session, params)

    mocker.patch("TIPCommon.rest.auth.get_adc", return_value=(mock_creds, "test-project"))
    # Also patch where it's directly imported
    try:
        mocker.patch("gmail.core.GoogleGmailUtils.get_adc", return_value=(mock_creds, "test-project"))
    except:
        pass
    try:
        mocker.patch("cloud_logging.core.utils.get_adc", return_value=(mock_creds, "test-project"))
    except:
        pass
    try:
        mocker.patch("vertex_ai.core.utils.get_adc", return_value=(mock_creds, "test-project"))
    except:
        pass


@pytest.fixture(autouse=True)
def mock_google_adc(mocker):
    """Mock the ADC to prevent DefaultCredentialsError in CI environments."""
    mock_creds = mocker.Mock()
    mock_creds.universe_domain = "googleapis.com"
    mocker.patch("google.auth.default", return_value=(mock_creds, "test-project"))
    mocker.patch("TIPCommon.rest.auth.get_adc", return_value=(mock_creds, "test-project"))
    try:
        mocker.patch("core.utils.get_adc", return_value=(mock_creds, "test-project"))
    except Exception:
        pass
    try:
        mocker.patch("core.GoogleGmailUtils.get_adc", return_value=(mock_creds, "test-project"))
    except Exception:
        pass

