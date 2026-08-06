from __future__ import annotations

import pytest
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from ellio.tests.core.product import Ellio
from ellio.tests.core.session import EllioSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def ellio() -> Ellio:
    return Ellio()


@pytest.fixture(autouse=True)
def script_session(monkeypatch: pytest.MonkeyPatch, ellio: Ellio) -> EllioSession:
    """Mock the session the ELLIO manager creates, and expose request history."""
    session: EllioSession = EllioSession(ellio)
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda *_: session)
        monkeypatch.setattr("requests.Session", lambda: session)
    return session


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch, ellio: Ellio) -> EllioSession:
    """Mock the SDK's own session (entity updates, insights)."""
    session: EllioSession = EllioSession(ellio)
    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    yield session
