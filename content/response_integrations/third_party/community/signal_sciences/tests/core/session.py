from __future__ import annotations

from typing import Iterable

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from .product import SignalSciencesProduct


class SignalSciencesSession(MockSession[MockRequest, MockResponse, SignalSciencesProduct]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.test_connectivity,
            self.list_sites,
            self.get_whitelist,
            self.get_blacklist,
            self.add_whitelist_item,
            self.add_blacklist_item,
            self.delete_whitelist_item,
            self.delete_blacklist_item,
        ]

    @router.get(r"/api/v0/corps/[^/]+")
    def test_connectivity(self, _: MockRequest) -> MockResponse:
        return MockResponse(content={"name": "mock_corp"}, status_code=200)

    @router.get(r"/api/v0/corps/[^/]+/sites")
    def list_sites(self, _: MockRequest) -> MockResponse:
        return MockResponse(content=self._product.get_sites(), status_code=200)

    @router.get(r"/api/v0/corps/[^/]+/sites/[^/]+/whitelist")
    def get_whitelist(self, request: MockRequest) -> MockResponse:
        site_name = request.url.path.split("/")[-2]
        return MockResponse(content=self._product.get_whitelist(site_name), status_code=200)

    @router.get(r"/api/v0/corps/[^/]+/sites/[^/]+/blacklist")
    def get_blacklist(self, request: MockRequest) -> MockResponse:
        site_name = request.url.path.split("/")[-2]
        return MockResponse(content=self._product.get_blacklist(site_name), status_code=200)

    @router.put(r"/api/v0/corps/[^/]+/sites/[^/]+/whitelist")
    def add_whitelist_item(self, request: MockRequest) -> MockResponse:
        site_name = request.url.path.split("/")[-2]
        payload = get_request_payload(request)
        item = self._product.add_whitelist_item(site_name, payload)
        return MockResponse(content=item, status_code=200)

    @router.put(r"/api/v0/corps/[^/]+/sites/[^/]+/blacklist")
    def add_blacklist_item(self, request: MockRequest) -> MockResponse:
        site_name = request.url.path.split("/")[-2]
        payload = get_request_payload(request)
        item = self._product.add_blacklist_item(site_name, payload)
        return MockResponse(content=item, status_code=200)

    @router.delete(r"/api/v0/corps/[^/]+/sites/[^/]+/whitelist/[^/]+")
    def delete_whitelist_item(self, request: MockRequest) -> MockResponse:
        parts = request.url.path.split("/")
        site_name = parts[-3]
        item_id = parts[-1]
        self._product.delete_whitelist_item(site_name, item_id)
        return MockResponse(content={}, status_code=200)

    @router.delete(r"/api/v0/corps/[^/]+/sites/[^/]+/blacklist/[^/]+")
    def delete_blacklist_item(self, request: MockRequest) -> MockResponse:
        parts = request.url.path.split("/")
        site_name = parts[-3]
        item_id = parts[-1]
        self._product.delete_blacklist_item(site_name, item_id)
        return MockResponse(content={}, status_code=200)
