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
import sys
import os
import soar_sdk
sys.path.insert(0, os.path.dirname(soar_sdk.__file__))


import pathlib
pytest_plugins = ("integration_testing.conftest",)
import sys
import os
import soar_sdk
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
from SiemplifyBase import SiemplifyBase
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
@pytest.fixture(name="google_chronicle_ai_agents")
def google_chronicle_ai_agents_product() -> GoogleSecOpsAiAgents:
    yield GoogleSecOpsAiAgents()


@pytest.fixture(name="script_session", autouse=True)
def google_chronicle_ai_agents_script_session(
    monkeypatch: pytest.MonkeyPatch,
    google_chronicle_ai_agents: GoogleSecOpsAiAgents,
) -> GoogleSecOpsAiAgentsSession:
  """
    Create a script session and patch the environment for action tests.
    This fixture replicates the old, working test setup.
    """
  session = GoogleSecOpsAiAgentsSession(google_chronicle_ai_agents)
  if not use_live_api():
    # Patch session creation used by the authenticator
    monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
    monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    monkeypatch.setattr(SiemplifyBase, "_create_remote_session", lambda *_: session)
    monkeypatch.setattr(
        google.auth.transport.requests.AuthorizedSession,
        "__new__",
        lambda *_, **__: session,
    )
    # Patch for internal SiemplifyAction SDK calls (like fetching alert details)
    monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    monkeypatch.setattr(Siemplify, "create_session", lambda *_: session)

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
    
    # Patch _load_current_alert to avoid localhost API calls
    class MockAlert:
        @property
        def additional_properties(self):
            return {"SiemAlertId": "alert-123"}
            
        @property
        def alert_group_identifier(self):
            return "alert-123"
    
    # Patch create_soar_action to inject a mocked alert into the returned action
    import TIPCommon.base.action.base_action
    original_create = TIPCommon.base.action.base_action.create_soar_action
    
    def mock_create_soar_action():
        print("MOCK CREATE SOAR ACTION CALLED")
        action = original_create()
        action._SiemplifyAction__current_alert = MockAlert()
        # Also patch load_case_data just in case it tries to reset it
        action.load_case_data = lambda *args: None
        return action
        
    monkeypatch.setattr(TIPCommon.base.action.base_action, "create_soar_action", mock_create_soar_action)

    # Patch the credential fetching to return a mock object
    monkeypatch.setattr(
            "google_sec_ops_ai_agents.core.authenticator.get_secops_siem_tenant_credentials",
            lambda *_, **__: MagicMock(),
        )

  yield session


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

