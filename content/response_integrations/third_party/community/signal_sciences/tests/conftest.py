from __future__ import annotations

import pytest
from integration_testing.common import use_live_api

from signal_sciences.tests.core.product import SignalSciences
from signal_sciences.tests.core.session import SignalSciencesSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def signal_sciences() -> SignalSciences:
    """Provides a SignalSciences mock product instance."""
    return SignalSciences()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    signal_sciences: SignalSciences,
) -> SignalSciencesSession:
    """Provides a SignalSciencesSession instance and patches requests."""
    session = SignalSciencesSession(signal_sciences)

    if not use_live_api():
        # Patch requests.Session
        monkeypatch.setattr("requests.Session", lambda: session)

    return session


@pytest.fixture(autouse=True)
def sdk_session(script_session: SignalSciencesSession) -> SignalSciencesSession:
    """Alias for script_session to provide a consistent session object for SDK mocking."""
    return script_session
