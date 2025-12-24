from __future__ import annotations

import pytest
from integration_testing.common import use_live_api
from TIPCommon.base.utils import CreateSession

from .core.product import Telegram
from .core.session import TelegramSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def telegram() -> Telegram:
    return Telegram()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    telegram: Telegram,
) -> TelegramSession:
    """Mock telegram scripts' session and get back an object to view request history"""
    session: TelegramSession = TelegramSession(telegram)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)

    return session
