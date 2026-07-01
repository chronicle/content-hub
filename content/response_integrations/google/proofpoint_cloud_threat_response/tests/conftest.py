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


import soar_sdk

# Provide integration_testing fixtures
pytest_plugins = ("integration_testing.conftest",)

# Alias all top-level soar_sdk modules to themselves to unify the namespace for mocks
for _, name, _ in pkgutil.iter_modules(soar_sdk.__path__):
    if name not in sys.modules:
        try:
            sys.modules[name] = __import__(f"soar_sdk.{name}", fromlist=[None])
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



from urllib.parse import urljoin

import pytest

from TIPCommon.base.utils import CreateSession
from SiemplifyBase import SiemplifyBase

from ..core.api_client import (
    ProofpointCloudThreatResponseApiClient,
    ApiParameters,
)
from ..core.auth import (
    AuthenticatedSession,
    SessionAuthenticationParameters,
)
from ..core.data_models import (
    IntegrationParameters,
)
from ..core.constants import AUTH_URL

from integration_testing.common import use_live_api
from integration_testing.logger import Logger
from ..tests.common import CONFIG
from ..tests.core.product import (
    ProofpointCloudThreatResponse,
)
from ..tests.core.session import (
    ProofpointCloudThreatResponseSession,
)


@pytest.fixture(name="proofpoint_ctr")
def proofpoint_ctr_product() -> ProofpointCloudThreatResponse:
    yield ProofpointCloudThreatResponse()


@pytest.fixture(name="script_session", autouse=True)
def proofpoint_ctr_script_session(
    monkeypatch: pytest.MonkeyPatch,
    proofpoint_ctr: ProofpointCloudThreatResponse,
) -> ProofpointCloudThreatResponseSession:
    """Create script session"""
    session = ProofpointCloudThreatResponseSession(proofpoint_ctr)
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_, **__: session)
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
        monkeypatch.setattr(SiemplifyBase, "_create_remote_session", lambda *_: session)

    yield session


@pytest.fixture(name="manager")
def proofpoint_ctr_manager() -> ProofpointCloudThreatResponseApiClient:
    """proofpoint_ctr manager"""
    api_root: str = CONFIG["API Root"]
    client_id: str = CONFIG["Client ID"]
    client_secret: str = CONFIG["Client Secret"]
    verify_ssl: bool = CONFIG["Verify SSL"]

    logger = Logger()

    api_params = ApiParameters(api_root=api_root)

    integration_params = IntegrationParameters(
        api_root=api_root,
        client_id=client_id,
        client_secret=client_secret,
        verify_ssl=verify_ssl,
    )

    auth_session = AuthenticatedSession(
        logger=logger, configuration=integration_params, verify_ssl=verify_ssl
    )

    auth_params_for_session = SessionAuthenticationParameters(
        client_id=client_id,
        client_secret=client_secret,
        auth_url=urljoin(api_root, AUTH_URL),
        verify_ssl=verify_ssl,
    )
    auth_session.authenticate_session(auth_params_for_session)

    yield ProofpointCloudThreatResponseApiClient(
        authenticated_session=auth_session,
        configuration=api_params,
        logger=logger,
    )


@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session


