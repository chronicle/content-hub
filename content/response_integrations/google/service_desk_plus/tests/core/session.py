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

from ...tests.common import ADD_REQUEST_MOCK, REQUEST
from ...tests.core.product import ServiceDeskPlus
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class ServiceDeskPlusSession(MockSession[MockRequest, MockResponse, ServiceDeskPlus]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [self.handle_request]

    @router.get(r"/sdpapi/request/")
    def handle_request(self, request: MockRequest) -> MockResponse:
        params = request.kwargs.get("params") or (request.args[0] if len(request.args) > 0 else {})
        operation_name = params.get("OPERATION_NAME")
        requests = self._product.get_requests()

        if operation_name == "ADD_REQUEST":
            if "FailSubject" in str(
                params.get("INPUT_DATA", "")
            ):
                return MockResponse(
                    content='<operation><result><status>Failed</status><message>Failed</message></result></operation>'
                )
            return MockResponse(
                content='<operation><result><status>Success</status><message>Request Added</message></result><Details><parameter><name>workorderid</name><value>12345</value></parameter></Details></operation>'
            )

        if operation_name == "GET_REQUESTS":
            # get_requests expects bypass=True, meaning it parses with xmltodict
            return MockResponse(
                content='<API><response><operation><Details><record><parameter><name>workorderid</name><value>12345</value></parameter><parameter><name>subject</name><value>Test Subject</value></parameter><parameter><name>description</name><value>Test Description</value></parameter></record></Details></operation></response></API>'
            )

        return MockResponse(
            content=f'<operation><result><status>Failed</status><message>Unknown operation {operation_name}</message></result></operation>',
            status_code=400,
        )
