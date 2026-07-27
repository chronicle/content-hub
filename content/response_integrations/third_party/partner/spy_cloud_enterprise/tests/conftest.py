from __future__ import annotations

from typing import Iterable
from unittest.mock import MagicMock, patch

import pytest
from integration_testing import router
from integration_testing.common import use_live_api
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction
from soar_sdk.SiemplifyBase import SiemplifyBase
from TIPCommon.base.utils import CreateSession

pytest_plugins = ("integration_testing.conftest",)


class SpyCloudMockSession(MockSession[MockRequest, MockResponse, None]):
    """Minimal SecOps SDK session stub.

    Actions that enrich entities call back into the SecOps server (UpdateEntities,
    CreateCaseInsight). The vendor-facing SpyCloud API itself is mocked separately
    via the ``spycloud_sdk`` fixture, so only these SDK endpoints need routing here.
    """

    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [self.update_entities, self.create_case_insight]

    @router.post(r"/api/external/v1/sdk/UpdateEntities")
    def update_entities(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)

    @router.post(r"/api/external/v1/sdk/CreateCaseInsight")
    def create_case_insight(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)


@pytest.fixture(autouse=True)
def script_session(monkeypatch: pytest.MonkeyPatch) -> SpyCloudMockSession:
    """Mock the scripts' session and register the SDK routes actions rely on."""
    session = SpyCloudMockSession()
    if not use_live_api():
        monkeypatch.setattr(CreateSession, "create_session", lambda: session)
        monkeypatch.setattr("requests.Session", lambda: session)
    return session


@pytest.fixture(autouse=True)
def sdk_session(monkeypatch: pytest.MonkeyPatch) -> SpyCloudMockSession:
    """Mock the SDK session used for SecOps server calls."""
    session = SpyCloudMockSession()
    if not use_live_api():
        monkeypatch.setattr(SiemplifyBase, "create_session", lambda *_: session)
    return session


@pytest.fixture
def spycloud_sdk() -> MagicMock:
    """Mock SpyCloud SDK with a successful breach catalog ping by default."""
    sdk = MagicMock()
    # The action uses the SDK as a context manager (`with SpyCloudSDK(...) as sdk`),
    # so __enter__ must return the same mock for the ping stubs to take effect.
    sdk.__enter__.return_value = sdk
    sdk.breach_catalog.ping.return_value = True
    # Sensible defaults for the data-returning actions; tests override as needed.
    sdk.breach_data.watchlist.return_value = []
    sdk.breach_catalog.catalog.return_value = []
    return sdk


@pytest.fixture(autouse=True)
def patch_spycloud_sdk(spycloud_sdk: MagicMock):
    """Patch the SpyCloudSDK used by actions so no real HTTP calls are made.

    Only Ping calls the SpyCloud API directly. Get Watchlist Exposures reads the
    exposures already attached to the case and makes no API calls, so it does not
    need (or import) the SDK.
    """
    with patch(
        "spy_cloud_enterprise.actions.Ping.SpyCloudSDK",
        return_value=spycloud_sdk,
    ):
        yield
