from __future__ import annotations

import pytest
from integration_testing.common import use_live_api

from .core.product import Abnormal
from .core.session import AbnormalSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def abnormal() -> Abnormal:
    return Abnormal()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    abnormal: Abnormal,
) -> AbnormalSession:
    """Mock the Abnormal scripts' session and return an object to view request history."""
    session: AbnormalSession = AbnormalSession(abnormal)

    if not use_live_api():
        monkeypatch.setattr("requests.Session", lambda: session)

    return session
