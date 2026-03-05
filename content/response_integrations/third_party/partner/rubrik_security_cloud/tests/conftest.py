from __future__ import annotations

import pytest
import requests
from integration_testing.common import use_live_api
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

from rubrik_security_cloud.tests.core.product import RubrikSecurityCloud
from rubrik_security_cloud.tests.core.session import RubrikSession

pytest_plugins = ("integration_testing.conftest",)


@pytest.fixture
def rubrik() -> RubrikSecurityCloud:
    return RubrikSecurityCloud()


@pytest.fixture(autouse=True)
def script_session(
    monkeypatch: pytest.MonkeyPatch,
    rubrik: RubrikSecurityCloud,
) -> RubrikSession:
    session: RubrikSession = RubrikSession(rubrik)

    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr(requests, "Session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)
        monkeypatch.setattr(requests, "post", session.post)

    return session


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch, rubrik: RubrikSecurityCloud) -> RubrikSession:
    session: RubrikSession = RubrikSession(rubrik)

    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)

    yield session
