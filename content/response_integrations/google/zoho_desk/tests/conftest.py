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

import os
import sys
import pkgutil
import pathlib


import soar_sdk

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

import pytest
from TIPCommon.base.utils import CreateSession
from integration_testing.common import use_live_api
from ..tests.core.session import ZohoDeskSession
from ..tests.core.zoho_desk import ZohoDesk


@pytest.fixture(name="zoho_desk")
def zoho_desk_product() -> ZohoDesk:
    yield ZohoDesk()


@pytest.fixture(name="script_session", autouse=True)
def zoho_desk_script_session(
    monkeypatch: pytest.MonkeyPatch,
    zoho_desk: ZohoDesk,
) -> ZohoDeskSession:
    """Create script session"""
    try:
        session: ZohoDeskSession = ZohoDeskSession(zoho_desk)
        if not use_live_api():
            monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
    except Exception as e:
        import traceback
        with open("/Users/haggit/PycharmProjects/marketplace/zoho_fixture_error.txt", "w") as f:
            f.write(traceback.format_exc())
        raise

    yield session


@pytest.fixture(name="zoho_desk_manager")
def zoho_desk_manager_fixture(script_session: ZohoDeskSession):
    from ..core.ZohoDeskApiManager import ZohoDeskApiClient
    from ..core.datamodels import IntegrationParameters
    from integration_testing.logger import Logger
    
    api_root = "https://desk.zoho.com/api/v1/"
    params = IntegrationParameters(
        api_root=api_root,
        oauth_token="dummy_token",
        verify_ssl=False,
        siemplify_logger=Logger(),
    )
    return ZohoDeskApiClient(session=script_session, params=params)

@pytest.fixture(name="sdk_session", autouse=True)
def sdk_session_fixture(script_session: ZohoDeskSession) -> ZohoDeskSession:
    return script_session

def pytest_runtest_logreport(report):
    if report.when == "call" and report.outcome == "failed":
        with open("/Users/haggit/PycharmProjects/marketplace/pytest_failures.txt", "a") as f:
            f.write(f"FAILED: {report.nodeid} - {report.longrepr}\n")
    elif report.when == "setup" and report.outcome == "failed":
        with open("/Users/haggit/PycharmProjects/marketplace/pytest_failures.txt", "a") as f:
            f.write(f"SETUP FAILED: {report.nodeid} - {report.longrepr}\n")
