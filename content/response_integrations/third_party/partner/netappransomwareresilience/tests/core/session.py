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
        try:
            token_data = self._product.get_token()
            return MockResponse(content=token_data, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=401)

    @router.post(r".*/enrich/ip-address")
    def enrich_ip_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle enrich IP address requests."""
        try:
            result = self._product.get_enrich_ip()
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r".*/enrich/storage")
    def enrich_storage_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle enrich storage requests."""
        try:
            result = self._product.get_enrich_storage()
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.get(r".*/job/status")
    def check_job_status_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle check job status requests."""
        try:
            result = self._product.get_check_job_status()
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r".*/storage/take-snapshot")
    def take_snapshot_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle take snapshot requests."""
        try:
            result = self._product.get_take_snapshot()
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)

    @router.post(r".*/storage/take-volume-offline")
    def volume_offline_endpoint(self, request: MockRequest) -> MockResponse:
        """Handle volume offline requests."""
        try:
            result = self._product.get_volume_offline()
            return MockResponse(content=result, status_code=200)
        except Exception as e:
            return MockResponse(content={"error": str(e)}, status_code=400)
