
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


import soar_sdk

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

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

# Add SDK internal modules to sys.path to support flat imports within the SDK and TIPCommon

# Add parent directory and integration directory to sys.path to support internal module resolution

import pytest

from TIPCommon.base.utils import CreateSession
from SiemplifyBase import SiemplifyBase

from azure_monitor.core.api_client import (
    AzureMonitorApiClient,
    ApiParameters,
)
from integration_testing.common import use_live_api
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.logger import Logger
from azure_monitor.tests.common import CONFIG
from azure_monitor.tests.core.product import AzureMonitor
from azure_monitor.tests.core.session import AzureMonitorSession


@pytest.fixture(name="azure_monitor")
def azure_monitor_product() -> AzureMonitor:
    yield AzureMonitor()


@pytest.fixture(name="script_session", autouse=True)
def azure_monitor_script_session(
    monkeypatch: pytest.MonkeyPatch,
    azure_monitor: AzureMonitor,
) -> AzureMonitorSession:
    """Create script session"""
    session: AzureMonitorSession[MockRequest, MockResponse, AzureMonitor] = (
        AzureMonitorSession(azure_monitor)
    )
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
        monkeypatch.setattr(SiemplifyBase, "_create_remote_session", lambda *_: session)

    yield session


@pytest.fixture(name="manager")
def azure_monitor_manager(script_session: AzureMonitorSession) -> AzureMonitorApiClient:
    """azure_monitor_ manager"""
    api_root: str = CONFIG["API Root"]
    workspace_id: str = CONFIG["Workspace ID"]
    logger = Logger()
    api_params: ApiParameters = ApiParameters(api_root, workspace_id)

    yield AzureMonitorApiClient(script_session, api_params, logger)


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


