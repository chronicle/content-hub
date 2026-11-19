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
from integration_testing.logger import Logger
from zerofox.tests.common import CONFIG
from zerofox.tests.core.product import Zerofox
from zerofox.tests.core.session import ZerofoxSession
from zerofox.core.ZerofoxManager import ApiManager, ApiParameters


@pytest.fixture(name="zerofox")
def zerofox_product() -> Zerofox:
    yield Zerofox()


@pytest.fixture(name="script_session", autouse=True)
def zerofox_script_session(
    monkeypatch: pytest.MonkeyPatch,
    zerofox: Zerofox,
) -> ZerofoxSession:
    session = ZerofoxSession(zerofox)
    """Create script session"""
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
    yield session


@pytest.fixture(name="manager")
def zerofox_manager(script_session: ZerofoxSession) -> ApiManager:
    """Zerofox manager"""
    api_root: str = CONFIG["API Root"]
    api_token: str = CONFIG["API Token"]

    logger = Logger()
    api_params: ApiParameters = ApiParameters(api_root, api_token)

    yield ApiManager(script_session, api_params, logger)

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
