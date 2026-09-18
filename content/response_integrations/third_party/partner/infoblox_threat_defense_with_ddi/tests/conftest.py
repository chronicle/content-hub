from __future__ import annotations

import pytest
from integration_testing.common import use_live_api

from .core.product import Infoblox
from .core.session import InfobloxSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def infoblox() -> Infoblox:
    return Infoblox()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    infoblox: Infoblox,
) -> InfobloxSession:
    """Mock the Infoblox scripts' session and return an object to view request history."""
    session: InfobloxSession = InfobloxSession(infoblox)

    if not use_live_api():
        monkeypatch.setattr("requests.Session", lambda: session)
        monkeypatch.setattr("requests.session", lambda: session)

    return session


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Skip the real sleep APIManager does between rate-limit retries."""
    monkeypatch.setattr("infoblox_threat_defense_with_ddi.core.APIManager.time.sleep", lambda *_a, **_k: None)
