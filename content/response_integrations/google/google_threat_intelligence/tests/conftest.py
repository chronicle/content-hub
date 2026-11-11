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

import cryptography.hazmat.primitives.serialization
import google.auth.transport.requests
import pytest
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from google_threat_intelligence.tests.core.product import (
    GoogleThreatIntelligenceProduct,
    GoogleThreatIntelligenceSdkProduct,
)
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSdkSession,
    GoogleThreatIntelligenceSession,
)
from integration_testing.common import use_live_api

# pylint: disable=redefined-outer-name


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
        google_threat_intelligence_product: GoogleThreatIntelligenceProduct,
) -> GoogleThreatIntelligenceSession:
    session = GoogleThreatIntelligenceSession(google_threat_intelligence_product)
    """Mock Google Threat Intellogence scripts' session and get back an object to
    view request history
    """

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr(
            google.auth.transport.requests.AuthorizedSession,
            "__new__",
            lambda *_, **__: session,
        )
        monkeypatch.setattr(
            cryptography.hazmat.primitives.serialization,
            "load_pem_private_key",
            lambda *_, **__: "private_key",
        )
    return session


@pytest.fixture
def google_threat_intelligence_product() -> GoogleThreatIntelligenceProduct:
    return GoogleThreatIntelligenceProduct()


@pytest.fixture(autouse=True)
def sdk_session(
    monkeypatch: pytest.MonkeyPatch,
    gti_sdk_product: GoogleThreatIntelligenceSdkProduct,
) -> GoogleThreatIntelligenceSdkSession:
    session = GoogleThreatIntelligenceSdkSession(gti_sdk_product)
    """Mock the SDK sessions and to view request and response history"""

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    return session


@pytest.fixture
def gti_sdk_product() -> GoogleThreatIntelligenceSdkProduct:
    return GoogleThreatIntelligenceSdkProduct()

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
