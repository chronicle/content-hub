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

from unittest.mock import MagicMock

import google.auth.transport.requests
import pytest
from google_sec_ops_ai_agents.core.api_client import (
    ChronicleInvestigationApiClient,
)
from google_sec_ops_ai_agents.core.data_models import (
    ApiParameters,
    IntegrationParameters,
)
from soar_sdk.SiemplifyAction import SiemplifyAction
from google_sec_ops_ai_agents.tests.common import CONFIG
from google_sec_ops_ai_agents.tests.core.product import (
    GoogleSecOpsAiAgents,
)
from google_sec_ops_ai_agents.tests.core.session import (
    GoogleSecOpsAiAgentsSession,
)
from integration_testing.common import use_live_api
from integration_testing.logger import Logger
from TIPCommon.base.utils import CreateSession
from soar_sdk.SiemplifyBase import SiemplifyBase
from soar_sdk.Siemplify import Siemplify


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
def api_client_fixture(
    monkeypatch, api_params: ApiParameters,
) -> ChronicleInvestigationApiClient:
    session = GoogleSecOpsAiAgentsSession(api_params)
    """Create a mock API client for unit tests."""
    session = MagicMock()
    logger = Logger()
    return session


# Fixtures for full integration/action tests
@pytest.fixture(name="google_chronicle_ai_agents")
def google_chronicle_ai_agents_product() -> GoogleSecOpsAiAgents:
    yield GoogleSecOpsAiAgents()


@pytest.fixture(name="script_session", autouse=True)
def google_chronicle_ai_agents_script_session(
    monkeypatch: pytest.MonkeyPatch,
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
) -> GoogleSecOpsAiAgentsSession:
  session = GoogleSecOpsAiAgentsSession(google_chronicle_ai_agents)
  """
    Create a script session and patch the environment for action tests.
    This fixture replicates the old, working test setup.
    """
  yield session

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
