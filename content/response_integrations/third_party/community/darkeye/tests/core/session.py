from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from darkeye.tests.core.product import DarkEye

if TYPE_CHECKING:
    from collections.abc import Iterable

HAVEIBEENRANSOM: str = "HaveIBeenRansom"
BREACH_HOUSE: str = "Breach House"


class DarkEyeSession(MockSession[MockRequest, MockResponse, DarkEye]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.haveibeenransom_search,
            self.breach_house_search,
            self.breach_house_me,
            self.update_entities,
        ]

    @router.get(r"/api/metadata/(domain|email)/[^/]+(/[0-9]+)?")
    def haveibeenransom_search(self, request: MockRequest) -> MockResponse:
        if HAVEIBEENRANSOM in self._product.failures:
            return MockResponse(content={"error": "denied"}, status_code=self._product.failures[HAVEIBEENRANSOM])
        parts: list[str] = request.url.path.split("/")
        field, term = parts[3], urllib.parse.unquote(parts[4])
        page: int = int(parts[5]) if len(parts) > 5 else 1
        return MockResponse(content=self._product.get_haveibeenransom_page(field, term, page))

    @router.get(r"/api/v1/search")
    def breach_house_search(self, request: MockRequest) -> MockResponse:
        if BREACH_HOUSE in self._product.failures:
            return MockResponse(content={"error": "denied"}, status_code=self._product.failures[BREACH_HOUSE])
        params: dict[str, str] = request.kwargs.get("params") or {}
        return MockResponse(content=self._product.get_breach_house_search(params["q"]))

    @router.get(r"/api/v1/me")
    def breach_house_me(self, _: MockRequest) -> MockResponse:
        if BREACH_HOUSE in self._product.failures:
            return MockResponse(content={"error": "denied"}, status_code=self._product.failures[BREACH_HOUSE])
        return MockResponse(content={"plan": "advanced"})

    @router.post(r"/api/external/v1/sdk/UpdateEntities")
    def update_entities(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={}, status_code=200)
