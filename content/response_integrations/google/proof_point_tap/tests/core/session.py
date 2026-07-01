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

import pathlib
from collections.abc import Iterable

from ...tests.core.product import ProofPointTAP
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class ProofPointTAPSession(MockSession[MockRequest, MockResponse, ProofPointTAP]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.get_campaign,
            self.search_events,
            self.list_campaigns,
            self.get_forensics,
        ]

    @router.get(r".*/v2/campaign/[a-fA-F0-9-]+/?$")
    def get_campaign(self, _: MockRequest) -> MockResponse:
        """Handle GET .*/v2/campaign/ requests"""
        test_ping_data = self._product.get_campaign()

        if not test_ping_data:
            return MockResponse(content={}, status_code=404)
        return MockResponse(content=test_ping_data.to_json(), status_code=200)

    @router.get(r".*/v2/siem/all")
    def search_events(self, _: MockRequest) -> MockResponse:
        """Handle POST .*/1.0/alerts/[0-9]+/append_notes/ requests"""
        events = self._product.get_events()

        return MockResponse(content=events.to_json(), status_code=200)

    @router.get(r".*/v2/campaign/ids")
    def list_campaigns(self, _: MockRequest) -> MockResponse:
        """Handle POST .*/1.0/alerts/[0-9]+/close/ requests"""
        list_campaigns_with_data = self._product.get_campaign()

        return MockResponse(content=list_campaigns_with_data.to_json(), status_code=200)

    @router.get(r".*/v2/forensics")
    def get_forensics(self, request: MockRequest) -> MockResponse:
        """Handle POST .*/1.0/alerts/[0-9]+/request_takedown/ requests"""
        forensics = self._product.get_threat_forensics()

        if "invalid" in str(request.url.query):
            return MockResponse(content={}, status_code=404)
        return MockResponse(content=forensics.to_json(), status_code=200)
