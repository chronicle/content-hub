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

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction
from TIPCommon.types import SingleJson

from misp.tests import common
from misp.tests.core.product import MISPProduct


class MISPSession(MockSession[MockRequest, MockResponse, MISPProduct]):
    """HTTP session interceptor mapping MISP API routes to mock product responses."""

    def __init__(self, product: MISPProduct) -> None:
        super().__init__(product)
        self.request_history: list[MockRequest] = []

    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.get_event,
            self.add_attribute,
            self.search_events,
            self.get_case_metadata,
        ]

    @router.get(r".*/api/external/.*")
    def get_case_metadata(self, request: MockRequest) -> MockResponse:
        """Handle internal platform CaseMetadata API requests gracefully."""
        return MockResponse(content={}, status_code=200)

    @router.post(r".*/events/restSearch/download/?")
    def search_events(self, request: MockRequest) -> MockResponse:
        """Handle POST requests for searching events to satisfy test_connectivity()."""
        self.request_history.append(request)
        return MockResponse(content={"response": [common.GET_EVENT]}, status_code=200)

    @router.get(r".*/events/[0-9]+")
    def get_event(self, request: MockRequest) -> MockResponse:
        """Handle GET requests for retrieving an event by ID."""
        self.request_history.append(request)
        event_id: str = request.url.path.split("/")[-1]

        try:
            event_data: SingleJson = self._product.get_event(event_id)
            return MockResponse(content=event_data, status_code=200)
        except common.EventIdNotFoundError:
            return MockResponse(
                content={"message": f"Event {event_id} not found."}, status_code=404
            )

    @router.post(r".*/attributes/add/[0-9]+")
    def add_attribute(self, request: MockRequest) -> MockResponse:
        """Handle POST requests for adding an attribute to an event."""
        self.request_history.append(request)
        event_id: str = request.url.path.split("/")[-1]
        req_json: SingleJson = request.kwargs.get("json", {})
        attribute_req: SingleJson = req_json.get("Attribute", {})

        try:
            self._product.add_attribute(attribute_req)
        except Exception as e:
            return MockResponse(content={"message": str(e)}, status_code=500)

        attr_type: str = attribute_req.get("type", "")
        response_payload: SingleJson = (
            common.ADD_ATTRIBUTE_HOSTNAME
            if attr_type == "hostname"
            else common.ADD_ATTRIBUTE_IP
        )

        payload_copy: SingleJson = dict(response_payload)
        if "Attribute" in payload_copy:
            payload_copy["Attribute"]["event_id"] = event_id

        return MockResponse(content=payload_copy, status_code=200)
