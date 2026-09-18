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
        sys.modules[f"soar_sdk.{name}"] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

import pathlib

import google.auth.transport.requests
import pytest
import requests

from TIPCommon.types import SingleJson

import cloud_logging.core.CloudLoggingAuthManager
from cloud_logging.core.CloudLoggingAuthManager import (
    CloudLoggingAuthManager,
)
from cloud_logging.core.CloudLoggingApiManager import (
    CloudLoggingApiManager,
)
from cloud_logging.core.datamodels import ApiManagerParams

from cloud_logging.tests.core.session import GoogleCloudApiSession
from integration_testing.common import get_def_file_content, use_live_api

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


@pytest.fixture(autouse=True)
def mock_google_adc(mocker):
    """Mock the ADC to prevent DefaultCredentialsError in CI environments."""
    mock_creds = mocker.Mock()
    mock_creds.universe_domain = "googleapis.com"
    mocker.patch("google.auth.default", return_value=(mock_creds, "test-project"))
    mocker.patch("TIPCommon.rest.auth.get_adc", return_value=(mock_creds, "test-project"))


@pytest.fixture(autouse=True)
def gcloud_api_script_session(
    monkeypatch: pytest.MonkeyPatch,
) -> GoogleCloudApiSession:
    """Mock Gcloud API session and get back an object to view request history"""
    session: GoogleCloudApiSession = GoogleCloudApiSession()
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *args, **kwargs: session,
        )
        monkeypatch.setattr(
            cloud_logging.core.CloudLoggingAuthManager,
            "AuthorizedSession",
            lambda *args, **kwargs: session,
        )

    yield session


@pytest.fixture
def gcloud_api_manager() -> CloudLoggingApiManager:
    """GoogleGmailApiManager manager"""
    api_root: str = CONFIG["API Root"]
    verify_ssl: bool = CONFIG["Verify SSL"]
    workload_identity_email = CONFIG["Workload Identity Email"]
    service_account_json = CONFIG["Service Account Json File Content"]
    project_id = CONFIG["Project ID"]
    quota_project_id = CONFIG["Quota Project ID"]
    organization_id = CONFIG["Organization ID"]
    auth_manager = CloudLoggingAuthManager(
        api_root=api_root,
        verify_ssl=verify_ssl,
        project_id=project_id,
        organization_id=organization_id,
        quota_project_id=quota_project_id,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
    )

    manager_params = ApiManagerParams(
        api_root=api_root,
        project_id=auth_manager.project_id,
        organization_id=organization_id,
    )
    return CloudLoggingApiManager(
        auth_manager.prepare_session(),
        params=manager_params,
    )


@pytest.fixture(name="sdk_session", autouse=True)
def sdk_session_fixture(script_session):
    return script_session
