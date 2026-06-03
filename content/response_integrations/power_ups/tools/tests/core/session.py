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

import json
from typing import Iterable

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from .product import Tools


class ToolsSession(MockSession[MockRequest, MockResponse, Tools]):
    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.get_workflows,
            self.rename_case,
            self.get_case_metadata,
            self.get_alerts_full_details,
            self.update_entities,
            self.get_alert_full_details,
            self.attach_workflow_to_case,
            self.update_alerts_additional,
        ]

    @router.get(r".*/dynamic-cases/GetCaseDetails/(?P<case_id>[^/]+)")
    @router.get(r".*/sdk/CaseMetadata/(?P<case_id>[^/]+)")
    def get_case_metadata(self, request: MockRequest) -> MockResponse:
        """Mock case overview details REST endpoint."""
        case_id = request.url.path.split("/")[-1]
        return MockResponse(content=self._product.get_case_metadata(case_id))

    @router.get(
        r".*/sdk/AlertsFullDetails/(?P<case_id>[^/]+)/(?P<populate_original_file>[^/]+)"
    )
    def get_alerts_full_details(self, request: MockRequest) -> MockResponse:
        """Mock alerts full details REST endpoint."""
        case_id = request.url.path.split("/")[-2]
        return MockResponse(content=self._product.get_alerts_full_details(case_id))

    @router.post(r".*/cases/GetWorkflowInstancesCards")
    def get_workflows(self, request: MockRequest) -> MockResponse:
        """Mock workflow instance query REST endpoint."""
        return MockResponse(content=self._product.get_workflows())

    @router.post(r".*/cases/RenameCase")
    def rename_case(self, request: MockRequest) -> MockResponse:
        """Mock rename case REST endpoint."""
        payload = request.kwargs.get("json") or {}
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                payload = {}
        new_title = payload.get("title", "Default New Title")
        return MockResponse(content=self._product.rename_case(new_title))

    @router.post(r".*/sdk/UpdateEntities")
    def update_entities(self, request: MockRequest) -> MockResponse:
        """Mock update entities REST endpoint."""
        return MockResponse(content={"isSuccessful": True})

    @router.post(r".*/sdk/AlertFullDetails")
    def get_alert_full_details(self, request: MockRequest) -> MockResponse:
        """Mock alert full details REST endpoint."""
        alerts = self._product.alerts_full_details
        return MockResponse(content=alerts[0] if alerts else {})

    @router.post(r".*/sdk/AttacheWorkflowToCase")
    def attach_workflow_to_case(self, request: MockRequest) -> MockResponse:
        """Mock attach workflow REST endpoint."""
        return MockResponse(content=True)

    @router.post(r".*/sdk/UpdateAlertsAdditional")
    def update_alerts_additional(self, request: MockRequest) -> MockResponse:
        """Mock update alerts additional data REST endpoint."""
        return MockResponse(content={"isSuccessful": True})
