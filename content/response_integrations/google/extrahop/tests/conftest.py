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
from extrahop.tests.common import CONFIG
from extrahop.tests.core.product import Extrahop
from extrahop.tests.core.session import ExtrahopSession
from extrahop.core.ExtrahopManager import (
    ExtrahopManager,
    ApiParameters,
)


@pytest.fixture(name="extrahop")
def extrahop_product() -> Extrahop:
    yield Extrahop()


@pytest.fixture(name="script_session", autouse=True)
def extrahop_script_session(
    monkeypatch: pytest.MonkeyPatch,
    extrahop: Extrahop,
) -> ExtrahopSession:
    session = ExtrahopSession(extrahop)
    """Create script session"""
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
    yield session


@pytest.fixture(name="manager")
def extrahop_manager(script_session: ExtrahopSession) -> ExtrahopManager:
    """Extrahop manager"""
    api_root: str = CONFIG["API Root"]
    client_id: str = CONFIG["Client ID"]
    client_secret: str = CONFIG["Client Secret"]

    logger = Logger()
    api_params: ApiParameters = ApiParameters(api_root, client_id, client_secret)

    yield ExtrahopManager(script_session, api_params, logger)

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
