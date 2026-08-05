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

"""Mock session for ThreatConnect tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import unquote

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from ..common import (
    ALERT_FULL_DETAILS_MOCK,
    INDICATOR_MOCK_RAW,
    INDICATORS_LIST_MOCK,
    SECURITY_LABELS_MOCK,
)
from .product import ThreatConnectProduct

if TYPE_CHECKING:
    from collections.abc import Iterable


class ThreatConnectSession(MockSession[MockRequest, MockResponse, ThreatConnectProduct]):
    """Mock session for ThreatConnect."""

    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.get_indicators,
            self.get_security_labels,
            self.get_indicator_by_summary,
            self.alert_full_details,
            self.create_case_insight,
            self.add_entity_link,
            self.update_entities,
        ]

    @router.get(r"/api/v3/indicators")
    def get_indicators(self, request: MockRequest) -> MockResponse:
        """Mock GET /api/v3/indicators."""
        return MockResponse(
            content=INDICATORS_LIST_MOCK,
            status_code=200,
        )

    @router.get(r"/api/v3/securityLabels")
    def get_security_labels(self, request: MockRequest) -> MockResponse:
        """Mock GET /api/v3/securityLabels."""
        return MockResponse(
            content=SECURITY_LABELS_MOCK,
            status_code=200,
        )

    @router.get(r"/api/v3/indicators/(?P<summary>[^/]+)")
    def get_indicator_by_summary(self, request: MockRequest) -> MockResponse:
        """Mock GET /api/v3/indicators/{summary}."""
        summary = request.url.path.split("/")[-1]
        decoded_summary = unquote(summary)

        if self._product:
            indicator_data = self._product.get_indicator(decoded_summary)
            if indicator_data:
                raw_indicator_dict = indicator_data.v3_raw_data.copy()
            else:
                return MockResponse(content={"message": "Indicator not found"}, status_code=404)
        else:
            raw_indicator_dict = INDICATOR_MOCK_RAW.copy()
        if "@" in decoded_summary:
            ind_type = "EmailAddress"
        elif "." in decoded_summary and "://" not in decoded_summary:
            ind_type = "Host"
        elif "://" in decoded_summary:
            ind_type = "URL"
        else:
            ind_type = "File"

        raw_indicator_dict["summary"] = decoded_summary
        raw_indicator_dict["type"] = ind_type

        return MockResponse(
            content={"data": raw_indicator_dict, "status": "Success"},
            status_code=200,
        )

    @router.post(r"/api/external/v1/sdk/AlertFullDetails")
    def alert_full_details(self, _: MockRequest) -> MockResponse:
        """Mock POST /api/external/v1/sdk/AlertFullDetails."""
        return MockResponse(
            content=ALERT_FULL_DETAILS_MOCK,
            status_code=200,
        )

    @router.post(r"/api/external/v1/sdk/CreateCaseInsight")
    def create_case_insight(self, _: MockRequest) -> MockResponse:
        """Mock POST /api/external/v1/sdk/CreateCaseInsight."""
        return MockResponse(content={}, status_code=200)

    @router.post(r"/api/external/v1/sdk/AddEntityLink")
    def add_entity_link(self, _: MockRequest) -> MockResponse:
        """Mock POST /api/external/v1/sdk/AddEntityLink."""
        return MockResponse(content={}, status_code=200)

    @router.post(r"/api/external/v1/sdk/UpdateEntities")
    def update_entities(self, _: MockRequest) -> MockResponse:
        """Mock POST /api/external/v1/sdk/UpdateEntities."""
        return MockResponse(content={}, status_code=200)
