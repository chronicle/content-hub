from __future__ import annotations

import pytest
from integration_testing.common import use_live_api
from TIPCommon.base.utils import CreateSession

from .core.product import Certly
from .core.session import CertlySession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def certly() -> Certly:
    return Certly()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    certly: Certly,
) -> CertlySession:
    session: CertlySession = CertlySession(certly)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)
        monkeypatch.setattr("requests.session", lambda: session)
        monkeypatch.setattr("requests.get", session.get)
        monkeypatch.setattr("requests.post", session.post)
        monkeypatch.setattr("requests.put", session.put)
        monkeypatch.setattr("requests.patch", session.patch)
        monkeypatch.setattr("requests.delete", session.delete)
        monkeypatch.setattr("requests.request", session.request)

    return session
