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

import google.auth.compute_engine
import google.auth.transport.requests
import pytest
import requests

from TIPCommon.transformation import convert_comma_separated_to_list
from TIPCommon.types import SingleJson

import google_cloud_api.core.GoogleCloudApiAuthManager
from google_cloud_api.core.GoogleCloudApiAuthManager import (
    AuthManager,
)
from google_cloud_api.core.GoogleCloudApiManager import (
    ApiManager,
)
from google_cloud_api.core.GoogleCloudApiDatamodels import (
    IntegrationPlaceholders,
)
from google_cloud_api.tests.core.session import (
    GoogleCloudApiSession
)
from integration_testing.common import get_def_file_content, use_live_api
from integration_testing.logger import Logger

pytest_plugins = ("integration_testing.conftest",)

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


@pytest.fixture(autouse=True)
def gcloud_api_script_session(
    monkeypatch: pytest.MonkeyPatch,
) -> GoogleCloudApiSession:
    """Mock Gcloud API session and get back an object to view request history"""
    session: GoogleCloudApiSession = (
        GoogleCloudApiSession()
    )
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *args, **kwargs: session
        )
        monkeypatch.setattr(
            google_cloud_api.core.GoogleCloudApiAuthManager,
            "AuthorizedSession",
            lambda *args, **kwargs: session
        )
        monkeypatch.setattr(
            "TIPCommon.rest.auth.get_adc",
            lambda *args, **kwargs: (
                google.auth.compute_engine.Credentials(),
                CONFIG["Project ID"],
            ),
        )

    yield session


@pytest.fixture
def gcloud_api_manager() -> ApiManager:
    """GoogleGmailApiManager manager"""
    verify_ssl: bool = CONFIG["Verify SSL"]
    workload_identity_email = CONFIG["Workload Identity Email"]
    service_account_json = CONFIG["Service Account Json File Content"]
    oauth_scopes = convert_comma_separated_to_list(CONFIG["OAuth Scopes"])
    project_id = CONFIG["Project ID"]
    quota_project_id = CONFIG["Quota Project ID"]
    auth_manager = AuthManager(
        oauth_scopes=oauth_scopes,
        verify_ssl=verify_ssl,
        project_id=project_id,
        quota_project_id=quota_project_id,
        service_account_json=service_account_json,
        workload_identity_email=workload_identity_email,
    )

    organizations_id = CONFIG["Organization ID"]
    integration_placeholders = IntegrationPlaceholders(
        project_id=auth_manager.project_id,
        org_id=organizations_id
    )
    return ApiManager(
        auth_manager.prepare_session(),
        placeholders=integration_placeholders,
        logger=Logger()
    )

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
