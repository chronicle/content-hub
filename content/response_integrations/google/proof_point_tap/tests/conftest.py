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
import pytest

from TIPCommon.base.utils import CreateSession
from integration_testing.common import use_live_api
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from proof_point_tap.tests.common import CONFIG
from proof_point_tap.tests.core.product import ProofPointTAP
from proof_point_tap.tests.core.session import ProofPointTAPSession
from proof_point_tap.core.ProofPointTapManager import (
    ProofPointTapManager,
    ApiParameters,
)


@pytest.fixture(name="proof_point_tap")
def proof_point_tap_product() -> ProofPointTAP:
    yield ProofPointTAP()


@pytest.fixture(name="script_session", autouse=True)
def proof_point_tap_script_session(
    monkeypatch: pytest.MonkeyPatch,
    proof_point_tap: ProofPointTAP,
) -> ProofPointTAPSession:
    session = ProofPointTAPSession(proof_point_tap)
    """Create script session"""
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
    yield session


@pytest.fixture(name="manager")
def proof_point_tap_manager(
    script_session: ProofPointTAPSession,
) -> ProofPointTapManager:
    """Zerofox manager"""
    api_root: str = CONFIG["API Root"]
    api_params: ApiParameters = ApiParameters(api_root)

    yield ProofPointTapManager(script_session, api_params)

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
