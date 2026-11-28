from __future__ import annotations

import pytest
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from darkeye.tests.core.product import DarkEye
from darkeye.tests.core.session import DarkEyeSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def darkeye() -> DarkEye:
    return DarkEye()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    darkeye: DarkEye,
) -> DarkEyeSession:
    """Mock the scripts' session and get back an object to view request history."""
    session: DarkEyeSession = DarkEyeSession(darkeye)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)

    return session


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch, darkeye: DarkEye) -> DarkEyeSession:
    """Mock the SDK sessions and get it back to view request and response history."""
    session: DarkEyeSession = DarkEyeSession(darkeye)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

    return session
