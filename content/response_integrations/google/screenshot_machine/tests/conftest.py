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

from screenshot_machine.tests.core.product import ScreenshotMachine
from screenshot_machine.tests.core.session import ScreenshotMachineSession
from integration_testing.common import use_live_api


# pylint: disable=redefined-outer-name


@pytest.fixture
def screenshot_machine() -> ScreenshotMachine:
    yield ScreenshotMachine()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    screenshot_machine: ScreenshotMachine,
) -> ScreenshotMachine:
    session = ScreenshotMachineSession(screenshot_machine)
    """Mock zoho desk scripts' session and get back an object to view request history"""

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
    yield session

@pytest.fixture(name='sdk_session', autouse=True)
def sdk_session_fixture(script_session):
    return script_session
