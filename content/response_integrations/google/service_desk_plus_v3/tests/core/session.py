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
import ast

from ...tests.common import ADD_REQUEST_MOCK, REQUEST
from ...tests.core.product import ServiceDeskPlusV3
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction

class ServiceDeskPlusV3Session(MockSession[MockRequest, MockResponse, ServiceDeskPlusV3]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [self.get_requests, self.create_request]

    @router.get(r"/api/external/v1/sdk/CaseMetadata/.*")
    def get_case_metadata(self, request: MockRequest) -> MockResponse:
        return MockResponse(content={"environment": "mock_env"})

    @router.get(r"/api/v3/requests")
    def get_requests(self, request: MockRequest) -> MockResponse:
        headers = request.kwargs.get("headers", {})
        if headers.get("TECHNICIAN_KEY") == "invalid_key":
            return MockResponse(content={"response_status": {"status": "failed", "message": "Invalid key"}}, status_code=401)

        requests = self._product.get_requests()
        if requests:
            return MockResponse(content=requests[0].to_json())
        return MockResponse(content=REQUEST.to_json())

    @router.post(r"/api/v3/requests")
    def create_request(self, request: MockRequest) -> MockResponse:
        data = request.kwargs.get("data", {})
        input_data_str = data.get("input_data", "{}")
        try:
            input_data = ast.literal_eval(input_data_str)
        except Exception:
            return MockResponse(content={"response_status": {"status": "failed", "message": "Invalid input_data"}}, status_code=400)

        if "FailSubject" in input_data.get("request", {}).get("subject", ""):
            return MockResponse(content={"response_status": {"status": "failed", "message": "Failed"}}, status_code=400)

        return MockResponse(content=ADD_REQUEST_MOCK.to_json())
