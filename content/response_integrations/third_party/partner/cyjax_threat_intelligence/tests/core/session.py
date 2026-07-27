from __future__ import annotations

from typing import Iterable

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import (
    MockSession,
    Response,
    RouteFunction,
)

from cyjax_threat_intelligence.tests.core.product import CyjaxThreatIntelligence


class CyjaxSession(MockSession[MockRequest, MockResponse, CyjaxThreatIntelligence]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.ping_endpoint,
            self.enrich_iocs_endpoint,
            self.domain_monitor_endpoint,
            self.list_data_breaches_endpoint,
        ]

    @router.get(r"/v2/indicator-of-compromise$")
    def ping_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_ping(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r"/v2/indicator-of-compromise/enrichment")
    def enrich_iocs_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_enrich_iocs(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r"/v2/domain-monitor/potential-malicious-domain")
    def domain_monitor_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_domain_monitor(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r"/v2/data-leak/credentials")
    def list_data_breaches_endpoint(self, request: MockRequest) -> MockResponse:
        try:
            return MockResponse(content=self._product.get_list_data_breaches(), status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)
