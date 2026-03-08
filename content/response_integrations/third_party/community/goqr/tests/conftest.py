from __future__ import annotations

import pytest
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from goqr.tests.core.product import GOQR
from goqr.tests.core.session import GOQRSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def goqr() -> GOQR:
    return GOQR()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    goqr: GOQR,
) -> GOQRSession:
    """Mock GOQR scripts' session and get back an object to view request history"""
    session: GOQRSession = GOQRSession(goqr)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)

    return session


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch) -> GOQRSession:
    """Mock the SDK sessions and get it back to view request and response history"""
    session: GOQRSession = GOQRSession(goqr)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

    yield session
