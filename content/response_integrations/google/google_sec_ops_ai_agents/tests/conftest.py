from __future__ import annotations

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
pytest_plugins = ("integration_testing.conftest",)


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
    api_params: ApiParameters,
) -> ChronicleInvestigationApiClient:
    """Create a mock API client for unit tests."""
    session = MagicMock()
    logger = Logger()
    return ChronicleInvestigationApiClient(
        api_params=api_params,
        logger=logger,
        authenticated_session=session,
    )


# Fixtures for full integration/action tests
@pytest.fixture(name="google_sec_ops_ai_agents")
def google_sec_ops_ai_agents_product() -> GoogleSecOpsAiAgents:
    yield GoogleSecOpsAiAgents()


@pytest.fixture(name="google_chronicle_ai_agents")
def google_chronicle_ai_agents_product(
    google_sec_ops_ai_agents: GoogleSecOpsAiAgents,
) -> GoogleSecOpsAiAgents:
    yield google_sec_ops_ai_agents


@pytest.fixture(name="script_session", autouse=True)
def google_chronicle_ai_agents_script_session(
    monkeypatch: pytest.MonkeyPatch,
    google_sec_ops_ai_agents: GoogleSecOpsAiAgents,
) -> GoogleSecOpsAiAgentsSession:
  """
    Create a script session and patch the environment for action tests.
    This fixture replicates the old, working test setup.
    """
  session = GoogleSecOpsAiAgentsSession(google_sec_ops_ai_agents)
  if not use_live_api():
    # Patch session creation used by the authenticator
    monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
    
    # Patch SiemplifyAction and SiemplifyBase/Siemplify
    monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    monkeypatch.setattr(Siemplify, "create_session", lambda *_: session)

    # Patch for API URI generation to avoid 'domain' attribute error
    monkeypatch.setattr(
        "google_sec_ops_ai_agents.core.utils.get_google_secops_api_uri",
        lambda *_: "https://test.chronicle.security",
    )

    # Patch the final AuthorizedSession to prevent real auth
    monkeypatch.setattr(
        google.auth.transport.requests.AuthorizedSession,
        "__new__",
        lambda *_, **__: session,
    )

    # Patch get_context_property to fix the "service account email not found" error
    monkeypatch.setattr(
            SiemplifyAction,
            "get_context_property",
            lambda *_, **__: "test@example.com",
        )

    # Patch the credential fetching to return a mock object
    monkeypatch.setattr(
            "google_sec_ops_ai_agents.core.authenticator.get_secops_siem_tenant_credentials",
            lambda *_, **__: MagicMock(),
        )

  yield session
