from __future__ import annotations

from collections.abc import Iterator

import pytest
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase

from .core.product import PortnoxCloud
from .core.session import PortnoxCloudSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def portnox() -> PortnoxCloud:
    return PortnoxCloud()


@pytest.fixture(autouse=True)
def script_session(monkeypatch: pytest.MonkeyPatch, portnox: PortnoxCloud) -> PortnoxCloudSession:
    """Mock the session the Portnox Cloud client creates and expose its request history."""
    session = PortnoxCloudSession(portnox)
    if not use_live_api():
        monkeypatch.setattr("requests.Session", lambda: session)
    return session


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch, portnox: PortnoxCloud) -> Iterator[PortnoxCloudSession]:
    """Mock the SDK's own session, used for entity updates and insights."""
    session = PortnoxCloudSession(portnox)
    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    yield session
