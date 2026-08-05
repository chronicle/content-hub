from __future__ import annotations

from typing import Iterable

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from ellio.tests.core.product import Ellio


class EllioSession(MockSession[MockRequest, MockResponse, Ellio]):
    """Routes the ELLIO API endpoints the actions call to the in-memory product."""

    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.cti_lookup,
            self.cti_extended_lookup,
            self.cbs_lookup,
            self.blocklist_add,
            self.sdk_ok,
        ]

    @router.get(r"/v1/cti/lookup/.+")
    def cti_lookup(self, _: MockRequest) -> MockResponse:
        """Ping connectivity probe - any 200 confirms auth."""
        return MockResponse(content={"seen": False}, status_code=200)

    @router.get(r"/v1/cti/extended_lookup/.+")
    def cti_extended_lookup(self, request: MockRequest) -> MockResponse:
        ip = request.url.path.split("/")[-1]
        record = self._product.get_cti(ip)
        if record is None:
            return MockResponse(content={}, status_code=404)
        return MockResponse(content=record, status_code=200)

    @router.get(r"/v1/cbs/lookup")
    def cbs_lookup(self, request: MockRequest) -> MockResponse:
        ip = get_request_payload(request).get("ip", "")
        record = self._product.get_cbs(ip)
        if record is None:
            return MockResponse(content={"found": False}, status_code=200)
        return MockResponse(content=record, status_code=200)

    @router.post(r"/v1/edl/ip-rulesets/.+/rules")
    def blocklist_add(self, request: MockRequest) -> MockResponse:
        body = get_request_payload(request)
        result = self._product.add_blocklist_rule(body.get("ip", ""), body)
        return MockResponse(content=result, status_code=200)

    @router.post(r"/api/external/v1/sdk/.+")
    def sdk_ok(self, _: MockRequest) -> MockResponse:
        """Catch-all for the SDK's own platform calls (update entities, insights)."""
        return MockResponse(content={}, status_code=200)
