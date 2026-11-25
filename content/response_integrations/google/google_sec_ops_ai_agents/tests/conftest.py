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
        sys.modules[f'soar_sdk.{name}'] = flat_mod
        setattr(soar_sdk, name, flat_mod)
    except Exception:
        pass
sys.stdout = original_stdout

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import google.auth.transport.requests
import pytest
from google_sec_ops_ai_agents.core import authenticator
from google_sec_ops_ai_agents.core.api_client import (
    ChronicleInvestigationApiClient,
)
from google_sec_ops_ai_agents.core.data_models import (
    ApiParameters,
    IntegrationParameters,
)
from google_sec_ops_ai_agents.tests.common import CONFIG
from google_sec_ops_ai_agents.tests.core.product import (
    GoogleSecOpsAiAgents,
)
from google_sec_ops_ai_agents.tests.core.session import (
    GoogleSecOpsAiAgentsSession,
)
from integration_testing.common import use_live_api
from integration_testing.logger import Logger
from soar_sdk.Siemplify import Siemplify
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

if TYPE_CHECKING:
    from collections.abc import Iterator


# Fixtures for unit-testing individual managers
@pytest.fixture(name="integration_params")
def integration_params_fixture() -> IntegrationParameters:
    """Create integration parameters for unit tests."""
    return IntegrationParameters(
        api_root=CONFIG["API Root"],
        verify_ssl=True,
    )


@pytest.fixture(name="api_params")
def api_params_fixture(integration_params: IntegrationParameters) -> ApiParameters:
    """Create API parameters for unit tests."""
    return ApiParameters.from_integration_params(integration_params)


@pytest.fixture(name="api_client")
def api_client_fixture(api_params: ApiParameters) -> ChronicleInvestigationApiClient:
    """Create a mock API client for unit tests."""
    session = MagicMock()
    logger = Logger()
    return ChronicleInvestigationApiClient(api_params=api_params, logger=logger, authenticated_session=session)


# Fixtures for full integration/action tests
@pytest.fixture(name="google_chronicle_ai_agents")
def google_chronicle_ai_agents_product() -> Iterator[GoogleSecOpsAiAgents]:
    """Yield mock product instance for action tests."""
    yield GoogleSecOpsAiAgents()


@pytest.fixture(name="script_session", autouse=True)
def google_chronicle_ai_agents_script_session(
    monkeypatch: pytest.MonkeyPatch,
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
) -> Iterator[GoogleSecOpsAiAgentsSession]:
    """Create a script session and patch the environment for action tests."""
    session = GoogleSecOpsAiAgentsSession(google_chronicle_ai_agents)
    if not use_live_api():
        monkeypatch.delenv("CHRONICLE_SERVICE_ACCOUNT_EMAIL", raising=False)
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
        monkeypatch.setattr(google.auth.transport.requests.AuthorizedSession, "__new__", lambda *_, **__: session)
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
        monkeypatch.setattr(Siemplify, "create_session", lambda *_: session)
        monkeypatch.setattr(SiemplifyAction, "get_context_property", lambda *_, **__: "test@example.com")
        monkeypatch.setattr(authenticator, "get_secops_siem_tenant_credentials", lambda *_, **__: MagicMock())

    yield session


@pytest.fixture(name="sdk_session", autouse=True)
def sdk_session_fixture(script_session: GoogleSecOpsAiAgentsSession) -> GoogleSecOpsAiAgentsSession:
    """Route SOAR SDK session calls through script_session."""
    return script_session
