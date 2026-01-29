"""Pytest configuration and fixtures for Silverfort integration tests."""

from __future__ import annotations

import pytest
from integration_testing.common import use_live_api  # type: ignore[import-not-found]
from soar_sdk.SiemplifyBase import SiemplifyBase  # type: ignore[import-not-found]
from TIPCommon.base.utils import CreateSession  # type: ignore[import-not-found]

from silverfort.tests.core.product import MockSilverfort
from silverfort.tests.core.session import SilverfortSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def silverfort() -> MockSilverfort:
    """Create a mock Silverfort instance."""
    return MockSilverfort()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    silverfort: MockSilverfort,
) -> SilverfortSession:
    """Mock Silverfort scripts' session and get back an object to view request history."""
    session: SilverfortSession = SilverfortSession(silverfort)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)

    return session


@pytest.fixture(autouse=True)
def sdk_session(
    monkeypatch: pytest.MonkeyPatch,
    silverfort: MockSilverfort,
) -> SilverfortSession:
    """Mock the SDK sessions and get it back to view request and response history."""
    session: SilverfortSession = SilverfortSession(silverfort)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

    return session
