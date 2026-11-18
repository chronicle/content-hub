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

from urllib.parse import urljoin

import pytest
import soar_sdk  # noqa: F401

from TIPCommon.base.utils import CreateSession

from proofpoint_threat_protection.core.api_client import (
    ProofpointThreatProtectionApiClient,
    ApiParameters,
)
from proofpoint_threat_protection.core.auth import (
    AuthenticatedSession,
    SessionAuthenticationParameters,
)
from proofpoint_threat_protection.core.data_models import (
    IntegrationParameters,
)
from proofpoint_threat_protection.core.constants import AUTH_URL

from integration_testing.common import use_live_api
from integration_testing.logger import Logger
from proofpoint_threat_protection.tests.common import CONFIG
from proofpoint_threat_protection.tests.core.product import (
    ProofpointThreatProtection,
)
from proofpoint_threat_protection.tests.core.session import (
    ProofpointThreatProtectionSession,
)

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture(name="proofpoint_ctr")
def proofpoint_ctr_product() -> ProofpointThreatProtection:
    yield ProofpointThreatProtection()


@pytest.fixture(name="script_session", autouse=True)
def proofpoint_ctr_script_session(
    monkeypatch: pytest.MonkeyPatch,
    proofpoint_ctr: ProofpointThreatProtection,
) -> ProofpointThreatProtectionSession:
    session = ProofpointThreatProtectionSession(proofpoint_ctr)
    """Create script session"""
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_, **__: session)
    yield session


@pytest.fixture(name="manager")
def proofpoint_tp_manager() -> ProofpointThreatProtectionApiClient:
    """proofpoint_tp manager"""
    api_root: str = CONFIG["API Root"]
    client_id: str = CONFIG["Client ID"]
    client_secret: str = CONFIG["Client Secret"]
    verify_ssl: bool = CONFIG["Verify SSL"]
    cluster_id: str = CONFIG["Cluster ID"]

    logger: Logger = Logger()

    api_params: ApiParameters = ApiParameters(api_root=api_root, cluster_id=cluster_id)

    integration_params: IntegrationParameters = IntegrationParameters(
        api_root=api_root,
        client_id=client_id,
        client_secret=client_secret,
        verify_ssl=verify_ssl,
        cluster_id=cluster_id,
    )

    auth_session: AuthenticatedSession = AuthenticatedSession()

    auth_params_for_session: SessionAuthenticationParameters = (
        SessionAuthenticationParameters(
            client_id=client_id,
            client_secret=client_secret,
            auth_url=urljoin(api_root, AUTH_URL),
            verify_ssl=verify_ssl,
        )
    )
    auth_session.authenticate_session(auth_params_for_session)

    yield ProofpointThreatProtectionApiClient(
        authenticated_session=auth_session,
        configuration=api_params,
        logger=logger,
    )
