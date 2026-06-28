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
changed = True
while changed:
    changed = False
    for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
        if name not in sys.modules:
            try:
                sys.modules[name] = __import__(f"soar_sdk.{name}", fromlist=[None])
                changed = True
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

import web_risk.core.WebRiskAuthManager
from web_risk.core.WebRiskAuthManager import (
    AuthManager,
    AuthManagerParams,
)
from web_risk.core.WebRiskApiManager import (
    ApiManager,
)
from web_risk.tests.core.session import ApiSession
from web_risk.tests.core.product import Product
from integration_testing.common import get_def_file_content, use_live_api
from integration_testing.logger import Logger

CONFIG_PATH: pathlib.Path = pathlib.Path(__file__).parent / "config.json"
CONFIG: SingleJson = get_def_file_content(CONFIG_PATH)


# pylint: disable=redefined-outer-name
@pytest.fixture
def product() -> Product:
    return Product()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    product: Product,
) -> ApiSession:
    """Mock Gcloud API session and get back an object to view request history"""
    session: ApiSession = ApiSession(product)
    if not use_live_api():
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *args, **kwargs: session
        )
        monkeypatch.setattr(
            web_risk.core.WebRiskAuthManager,
            "AuthorizedSession",
            lambda *args, **kwargs: session
        )
        monkeypatch.setattr(
            "web_risk.core.WebRiskAuthManager.get_workload_sa_email",
            lambda *args, **kwargs: "Unknown Principal",
        )

    yield session


@pytest.fixture
def gcloud_api_manager() -> ApiManager:
    """GoogleGmailApiManager manager"""
    api_root = CONFIG["API Root"]
    verify_ssl: bool = CONFIG["Verify SSL"]
    workload_identity_email = CONFIG["Workload Identity Email"]
    service_account_json = CONFIG["Service Account Json File Content"]
    project_id = CONFIG["Project ID"]
    quota_project_id = CONFIG["Quota Project ID"]
    auth_manager = AuthManager(
        AuthManagerParams(
            verify_ssl=verify_ssl,
            project_id=project_id,
            quota_project_id=quota_project_id,
            service_account_json=service_account_json,
            workload_identity_email=workload_identity_email,
        )
    )

    return ApiManager(
        api_root=api_root,
        session=auth_manager.prepare_session(),
        project_id=auth_manager.project_id,
        logger=Logger()
    )


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


