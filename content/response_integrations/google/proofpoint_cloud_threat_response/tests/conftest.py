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

from urllib.parse import urljoin

import pytest

from TIPCommon.base.utils import CreateSession

from proofpoint_cloud_threat_response.core.api_client import (
    ProofpointCloudThreatResponseApiClient,
    ApiParameters,
)
from proofpoint_cloud_threat_response.core.auth import (
    AuthenticatedSession,
    SessionAuthenticationParameters,
)
from proofpoint_cloud_threat_response.core.data_models import (
    IntegrationParameters,
)
from proofpoint_cloud_threat_response.core.constants import AUTH_URL

from integration_testing.common import use_live_api
from integration_testing.logger import Logger
from proofpoint_cloud_threat_response.tests.common import CONFIG
from proofpoint_cloud_threat_response.tests.core.product import (
    ProofpointCloudThreatResponse,
)
from proofpoint_cloud_threat_response.tests.core.session import (
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
    session = ProofpointCloudThreatResponseSession(proofpoint_ctr)
    """Create script session"""
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_, **__: session)
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
