from __future__ import annotations

import pytest
import requests
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from netappransomwareresilience.tests.core.product import RansomwareResilience
from netappransomwareresilience.tests.core.session import RRSSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def rrs() -> RansomwareResilience:
    """Create a fresh RRS product state for each test."""
    return RansomwareResilience()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    rrs: RansomwareResilience,
) -> RRSSession:
    """Mock HTTP session for scripts using TIPCommon/requests.

    Intercepts requests.Session, requests.post, and CreateSession so that
    all HTTP calls from action code go through the mock router.
    """
    session: RRSSession = RRSSession(rrs)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)
        monkeypatch.setattr(requests, "post", session.post)

    return session


@pytest.fixture(autouse=True)
def sdk_session(
    monkeypatch: pytest.MonkeyPatch,
    rrs: RansomwareResilience,
) -> RRSSession:
    """Mock HTTP session for the SOAR SDK layer.

    Patches SiemplifyBase.create_session to use the mock session.
    """
    session: RRSSession = RRSSession(rrs)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

    yield session
