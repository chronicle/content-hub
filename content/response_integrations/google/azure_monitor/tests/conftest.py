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

import pytest
import soar_sdk  # noqa: F401
from integration_testing.common import use_live_api
from integration_testing.logger import Logger
from TIPCommon.base.utils import CreateSession

from azure_monitor.core.api_client import (
    ApiParameters,
    AzureMonitorApiClient,
)
from azure_monitor.tests.common import CONFIG
from azure_monitor.tests.core.product import AzureMonitor
from azure_monitor.tests.core.session import AzureMonitorSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture(name="azure_monitor")
def azure_monitor_product() -> AzureMonitor:
    return AzureMonitor()


@pytest.fixture(name="script_session", autouse=True)
def azure_monitor_script_session(
    monkeypatch: pytest.MonkeyPatch,
    azure_monitor: AzureMonitor,
) -> AzureMonitorSession:
    """Create script session."""
    session = AzureMonitorSession(azure_monitor)
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
    return session


@pytest.fixture(name="manager")
def azure_monitor_manager(script_session: AzureMonitorSession) -> AzureMonitorApiClient:
    """Create AzureMonitorApiClient fixture."""
    api_root: str = CONFIG["API Root"]
    workspace_id: str = CONFIG["Workspace ID"]
    logger = Logger()
    api_params: ApiParameters = ApiParameters(api_root, workspace_id)

    return AzureMonitorApiClient(script_session, api_params, logger)


@pytest.fixture(name="sdk_session", autouse=True)
def sdk_session_fixture(script_session: AzureMonitorSession) -> AzureMonitorSession:
    return script_session
