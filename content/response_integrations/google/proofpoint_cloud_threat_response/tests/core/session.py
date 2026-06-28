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
import pathlib

from collections.abc import Iterable

import json

from proofpoint_cloud_threat_response.tests.common import (
    MESSAGES_JSON,
    OAUTH_TOKEN_JSON,
)
from proofpoint_cloud_threat_response.tests.core.product import (
    ProofpointCloudThreatResponse,
)
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class ProofpointCloudThreatResponseSession(
    MockSession[MockRequest, MockResponse, ProofpointCloudThreatResponse]
):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.incidents_handler,
            self.get_incident_messages,
            get_oauth_token,
        ]

    @router.post(".*/api/v1/tric/incidents")
    def incidents_handler(self, request: MockRequest) -> MockResponse:
        """Handle incident-related requests."""
        payload = request.kwargs.get("json", {})
        if "filters" in payload:
            filters = payload.get("filters", {})
            query = json.dumps(filters, sort_keys=True)
            incidents = self._product.get_incidents(query)
            return MockResponse(
                status_code=200,
                content={"incidents": [incident.raw_data for incident in incidents]},
            )
        incidents = self._product.get_incidents("ping_query")
        return MockResponse(
            status_code=200,
            content={"incidents": [incident.raw_data for incident in incidents]},
        )

    @router.post("/api/v1/tric/incidents/[a-zA-Z0-9_-]+/messages")
    def get_incident_messages(self, _request: MockRequest) -> MockResponse:
        return MockResponse(status_code=200, content=MESSAGES_JSON)


@router.post("/v1/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """Get an OAuth token"""
    if (
        request.kwargs.get("data", {}).get("client_secret")
        == "invalid client secret"
    ):
        return MockResponse(
            content={
                "error": {
                    "message": (
                        "Failed to authenticate to Proofpoint Cloud Threat "
                        "Response"
                    ),
                    "errors": [{"errorMessage": "Wrong Credentials!"}],
                }
            },
            status_code=400,
        )

    return MockResponse(OAUTH_TOKEN_JSON)
