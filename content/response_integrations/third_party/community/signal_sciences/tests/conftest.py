from __future__ import annotations

import pytest
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from .core.product import SignalSciencesProduct
from .core.session import SignalSciencesSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def signal_sciences() -> SignalSciencesProduct:
    return SignalSciencesProduct()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    signal_sciences: SignalSciencesProduct,
) -> SignalSciencesSession:
    session: SignalSciencesSession = SignalSciencesSession(signal_sciences)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)

    return session


@pytest.fixture(autouse=True)
def sdk_session(
    monkeypatch: pytest.MonkeyPatch,
    signal_sciences: SignalSciencesProduct,
) -> SignalSciencesSession:
    session: SignalSciencesSession = SignalSciencesSession(signal_sciences)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

    yield session
