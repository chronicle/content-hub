from __future__ import annotations

import re
from typing import Iterable

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction
from signal_sciences.tests.core.product import SignalSciences
from TIPCommon.types import SingleJson


class SignalSciencesSession(MockSession[MockRequest, MockResponse, SignalSciences]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.get_corp,
            self.get_sites,
            self.get_allowlist,
            self.add_ip_to_allowlist,
            self.remove_ip_from_allowlist,
            self.get_blocklist,
            self.add_ip_to_blocklist,
            self.remove_ip_from_blocklist,
        ]

    def _extract_corp_name(self, path: str) -> str:
        match = re.search(r"/corps/([^/]+)", path)
        return match.group(1) if match else ""

    def _extract_site_name(self, path: str) -> str:
        match = re.search(r"/sites/([^/]+)", path)
        return match.group(1) if match else ""

    def _extract_item_id(self, path: str) -> str:
        return path.split("/")[-1]

    def _paginate(self, all_items: list, params: SingleJson) -> list:
        page = int(params.get("page", 1))
        limit = int(params.get("limit", 10))

        start = (page - 1) * limit
        end = start + limit
        if start >= len(all_items):
            return []
        return all_items[start:end]

    @router.get(r"/api/v0/corps/[^/]+$")
    def get_corp(self, request: MockRequest) -> MockResponse:
        corp_name = self._extract_corp_name(request.url.path)
        try:
            corp = self._product.get_corp(corp_name)
            return MockResponse(content=corp)
        except Exception as e:
            return MockResponse(content={"message": str(e)}, status_code=404)

    @router.get(r"/api/v0/corps/[^/]+/sites$")
    def get_sites(self, request: MockRequest) -> MockResponse:
        corp_name = self._extract_corp_name(request.url.path)
        params: SingleJson = get_request_payload(request)
        all_sites = self._product.get_sites(corp_name)
        paged_sites = self._paginate(all_sites, params)
        return MockResponse(content={"data": paged_sites})

    @router.get(r"/api/v0/corps/[^/]+/sites/[^/]+/whitelist$")
    def get_allowlist(self, request: MockRequest) -> MockResponse:
        corp_name = self._extract_corp_name(request.url.path)
        site_name = self._extract_site_name(request.url.path)
        if site_name == "non-existent-site":
            return MockResponse(content={"message": "Site not found"}, status_code=404)
        params: SingleJson = get_request_payload(request)
        items = self._product.get_allowlist(corp_name, site_name)
        paged_items = self._paginate(items, params)
        return MockResponse(content={"data": paged_items})

    @router.put(r"/api/v0/corps/[^/]+/sites/[^/]+/whitelist$")
    def add_ip_to_allowlist(self, request: MockRequest) -> MockResponse:
        corp_name = self._extract_corp_name(request.url.path)
        site_name = self._extract_site_name(request.url.path)
        try:
            payload: SingleJson = get_request_payload(request)
            ip_address = payload.get("source")
            note = payload.get("note", "")
            item = self._product.add_ip_to_allowlist(corp_name, site_name, ip_address, note)
            return MockResponse(content=item)
        except Exception as e:
            return MockResponse(content={"message": str(e)}, status_code=400)

    @router.delete(r"/api/v0/corps/[^/]+/sites/[^/]+/whitelist/[^/]+$")
    def remove_ip_from_allowlist(self, request: MockRequest) -> MockResponse:
        corp_name = self._extract_corp_name(request.url.path)
        site_name = self._extract_site_name(request.url.path)
        item_id = self._extract_item_id(request.url.path)
        self._product.remove_ip_from_allowlist(corp_name, site_name, item_id)
        return MockResponse(content={}, status_code=204)

    @router.get(r"/api/v0/corps/[^/]+/sites/[^/]+/blacklist$")
    def get_blocklist(self, request: MockRequest) -> MockResponse:
        corp_name = self._extract_corp_name(request.url.path)
        site_name = self._extract_site_name(request.url.path)
        if site_name == "non-existent-site":
            return MockResponse(content={"message": "Site not found"}, status_code=404)
        params: SingleJson = get_request_payload(request)
        items = self._product.get_blocklist(corp_name, site_name)
        paged_items = self._paginate(items, params)
        return MockResponse(content={"data": paged_items})

    @router.put(r"/api/v0/corps/[^/]+/sites/[^/]+/blacklist$")
    def add_ip_to_blocklist(self, request: MockRequest) -> MockResponse:
        corp_name = self._extract_corp_name(request.url.path)
        site_name = self._extract_site_name(request.url.path)
        try:
            payload: SingleJson = get_request_payload(request)
            ip_address = payload.get("source")
            note = payload.get("note", "")
            item = self._product.add_ip_to_blocklist(corp_name, site_name, ip_address, note)
            return MockResponse(content=item)
        except Exception as e:
            return MockResponse(content={"message": str(e)}, status_code=400)

    @router.delete(r"/api/v0/corps/[^/]+/sites/[^/]+/blacklist/[^/]+$")
    def remove_ip_from_blocklist(self, request: MockRequest) -> MockResponse:
        corp_name = self._extract_corp_name(request.url.path)
        site_name = self._extract_site_name(request.url.path)
        item_id = self._extract_item_id(request.url.path)
        self._product.remove_ip_from_blocklist(corp_name, site_name, item_id)
        return MockResponse(content={}, status_code=204)
