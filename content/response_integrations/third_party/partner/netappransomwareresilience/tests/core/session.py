from __future__ import annotations

from typing import Iterable

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from netappransomwareresilience.tests.core.product import RansomwareResilience


class RRSSession(MockSession[MockRequest, MockResponse, RansomwareResilience]):
    """Mock HTTP session that intercepts all RRS API calls.

    Routes requests to the appropriate product method based on URL pattern.
    """

    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        """Return all route handler functions."""
        return [
            self.oauth_token_endpoint,
            self.enrich_ip_endpoint,
            self.enrich_storage_endpoint,
            self.check_job_status_endpoint,
            self.take_snapshot_endpoint,
            self.volume_offline_endpoint,
        ]

    @router.post(r"/oauth/token")
    def oauth_token_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle OAuth token requests."""
        status_code = self._product.token_status_code
        if status_code and status_code >= 400:
            body = self._product.token_response or {"error": "authentication_failed"}
            return MockResponse(content=body, status_code=status_code)
        return MockResponse(content=self._product.get_token(), status_code=200)

    @router.post(r".*/enrich/ip-address")
    def enrich_ip_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle enrich IP address requests."""
        status_code = self._product.enrich_ip_status_code
        if status_code and status_code >= 400:
            body = self._product.enrich_ip_response or {"error": "request_failed"}
            return MockResponse(content=body, status_code=status_code)
        return MockResponse(content=self._product.get_enrich_ip(), status_code=200)

    @router.get(r".*/enrich/storage")
    def enrich_storage_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle enrich storage requests."""
        status_code = self._product.enrich_storage_status_code
        if status_code and status_code >= 400:
            body = self._product.enrich_storage_response or {"error": "request_failed"}
            return MockResponse(content=body, status_code=status_code)
        return MockResponse(content=self._product.get_enrich_storage(), status_code=200)

    @router.get(r".*/job/status")
    def check_job_status_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle check job status requests."""
        status_code = self._product.check_job_status_status_code
        if status_code and status_code >= 400:
            body = self._product.check_job_status_response or {"error": "request_failed"}
            return MockResponse(content=body, status_code=status_code)
        return MockResponse(content=self._product.get_check_job_status(), status_code=200)

    @router.post(r".*/storage/take-snapshot")
    def take_snapshot_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle take snapshot requests."""
        status_code = self._product.take_snapshot_status_code
        if status_code and status_code >= 400:
            body = self._product.take_snapshot_response or {"error": "request_failed"}
            return MockResponse(content=body, status_code=status_code)
        return MockResponse(content=self._product.get_take_snapshot(), status_code=200)

    @router.post(r".*/storage/take-volume-offline")
    def volume_offline_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle volume offline requests."""
        status_code = self._product.volume_offline_status_code
        if status_code and status_code >= 400:
            body = self._product.volume_offline_response or {"error": "request_failed"}
            return MockResponse(content=body, status_code=status_code)
        return MockResponse(content=self._product.get_volume_offline(), status_code=200)
