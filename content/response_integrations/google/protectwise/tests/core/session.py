# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from collections.abc import Iterable

from protectwise.tests import common
from protectwise.tests.core.product import ProtectwiseProduct
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction
from TIPCommon.types import SingleJson


class ProtectwiseSession(MockSession[MockRequest, MockResponse, ProtectwiseProduct]):
    """HTTP session interceptor mapping Protectwise REST routes to mock product responses."""

    def __init__(self, product: ProtectwiseProduct) -> None:
        super().__init__(product)
        self.request_history: list[MockRequest] = []

    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.get_token,
            self.get_events,
            self.download_pcap,
        ]

    @router.post(r".*/api/v1/token/?")
    def get_token(self, request: MockRequest) -> MockResponse:
        """Handle POST requests for authenticating and obtaining a session token."""
        self.request_history.append(request)
        return MockResponse(content=common.TOKEN_RESPONSE, status_code=200)

    @router.get(r".*/api/v1/events/?")
    def get_events(self, request: MockRequest) -> MockResponse:
        """Handle GET requests for querying security events in a timeframe."""
        self.request_history.append(request)
        try:
            events_data: SingleJson = self._product.get_events()
            return MockResponse(content=events_data, status_code=200)
        except Exception as e:
            return MockResponse(
                content={"error": {"info": str(e)}}, status_code=500
            )

    @router.get(r".*/api/v1/pcaps/events/.*")
    def download_pcap(self, request: MockRequest) -> MockResponse:
        """Handle GET requests for downloading PCAP files by event ID."""
        self.request_history.append(request)
        event_id: str = request.url.path.split("/")[-1]
        try:
            pcap_bytes: bytes = self._product.download_pcap(event_id)
            return MockResponse(content=pcap_bytes.decode("utf-8"), status_code=200)
        except common.EventIdNotFoundError:
            return MockResponse(
                content={"error": {"info": f"PCAP {event_id} not found"}},
                status_code=404,
            )
