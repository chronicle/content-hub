# Copyright 2025 Google LLC
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

from typing import Iterable

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from .product import EnrichmentProduct


class EnrichmentMockSession(MockSession[MockRequest, MockResponse, EnrichmentProduct]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.update_entities,
            self.create_entity,
            self.add_attachment,
            self.close_case,
            self.lookup_whois,
            self.lookup_ip,
        ]

    @router.post(r"/api/external/v1/sdk/UpdateEntities")
    def update_entities(self, _: MockRequest) -> MockResponse:
        """Mock endpoint for updating enriched entities in Chronicle SOAR."""
        return MockResponse(content={}, status_code=200)

    @router.post(r"/api/external/v1/sdk/CreateEntity")
    def create_entity(self, _: MockRequest) -> MockResponse:
        """Mock endpoint for creating related entities in Chronicle SOAR."""
        return MockResponse(content={}, status_code=200)

    @router.post(r"/api/external/v1/sdk/AddAttachment")
    def add_attachment(self, _: MockRequest) -> MockResponse:
        """Mock endpoint for adding attachments to alerts/cases."""
        return MockResponse(content={}, status_code=200)

    @router.post(r"/api/external/v1/sdk/Close")
    def close_case(self, _: MockRequest) -> MockResponse:
        """Mock endpoint for closing cases."""
        return MockResponse(content={}, status_code=200)

    @router.get(r"/api/v1/whois/.*")
    def lookup_whois(self, _: MockRequest) -> MockResponse:
        """Mock external endpoint for WHOIS domain lookups."""
        return MockResponse(content={"status": "success"}, status_code=200)

    @router.get(r"/api/v1/ip/.*")
    def lookup_ip(self, _: MockRequest) -> MockResponse:
        """Mock external endpoint for IP geographic lookups."""
        return MockResponse(content={"status": "success"}, status_code=200)
