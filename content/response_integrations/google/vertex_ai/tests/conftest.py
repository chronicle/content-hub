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
import os
import sys
import pkgutil
import pathlib


import pytest
import requests

import soar_sdk

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

# Alias all top-level soar_sdk modules to themselves to unify the namespace for mocks
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    if name not in sys.modules:
        try:
            sys.modules[name] = __import__(f"soar_sdk.{name}", fromlist=[None])
        except Exception:
            pass

# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon
sdk_dir = os.path.dirname(soar_sdk.__file__)
if sdk_dir not in sys.path:
    sys.path.insert(0, sdk_dir)

# Add parent directory and integration directory to sys.path to support internal module resolution
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
int_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if int_dir not in sys.path:
    sys.path.insert(0, int_dir)



import google.auth.transport.requests

from TIPCommon.types import SingleJson

import vertex_ai.core.VertexAIAuthManager
from ..core.VertexAIAuthManager import (
    AuthManager,
    AuthManagerParams,
)
from ..core.VertexAIApiManager import ApiManager
from ..tests.core.session import ApiSession
from integration_testing.common import get_def_file_content, use_live_api
from integration_testing.logger import Logger

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


@pytest.fixture(autouse=True)
def vertexai_script_session(
    mocker,
    monkeypatch: pytest.MonkeyPatch,
) -> ApiSession:
    """Mock Vertex AI session and get back an object to view request history"""
    session = ApiSession()
    # pylint: disable=protected-access
    session._auth_request = session.credentials = mocker.Mock()
    if not use_live_api():
        monkeypatch.setattr(
            "vertex_ai.core.VertexAIAuthManager.get_workload_sa_email",
            lambda *args, **kwargs: "Unknown Principal"
        )
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *args, **kwargs: session
        )
        monkeypatch.setattr(
            vertex_ai.core.VertexAIAuthManager,
            "AuthorizedSession",
            lambda *args, **kwargs: session
        )

    yield session


# pylint: disable=redefined-outer-name
@pytest.fixture
def vertexai_manager() -> ApiManager:
    """Vertex AI ApiManager."""
    api_root = CONFIG["API Root"]
    verify_ssl: bool = CONFIG["Verify SSL"]
    location_id = CONFIG["Location ID"]
    workload_identity_email = CONFIG["Workload Identity Email"]
    service_account_json = CONFIG["Service Account Json File Content"]
    project_id = CONFIG["Project ID"]
    auth_params = AuthManagerParams(
        verify_ssl=verify_ssl,
        project_id=project_id,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
    )
    auth_manager = AuthManager(auth_params)

    return ApiManager(
        api_root=api_root,
        session=auth_manager.prepare_session(),
        location_id=location_id,
        project_id=auth_manager.project_id,
        logger=Logger()
    )


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session



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

