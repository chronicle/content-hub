from __future__ import annotations

import pytest
from integration_testing.common import use_live_api

from .core.product import PagerDuty
from .core.session import PagerDutySession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def pagerduty() -> PagerDuty:
    return PagerDuty()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    pagerduty: PagerDuty,
) -> PagerDutySession:
    """Mock PagerDuty scripts' session and get back an object to view request history"""
    session: PagerDutySession = PagerDutySession(pagerduty)

    if not use_live_api():
        monkeypatch.setattr("requests.Session", lambda: session)

    return session
