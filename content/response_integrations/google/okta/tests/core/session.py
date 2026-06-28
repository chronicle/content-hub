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
from typing import Iterable
from http import HTTPStatus
import re

from okta.tests.core.product import (
    Product,
)
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction
from okta.tests.responses.api.common import USER_RESPONSE


class Session(MockSession[MockRequest, MockResponse, Product]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.get_user,
            self.send_itp_signal,
            self.clear_user_sessions,
            self.get_user_by_id,
        ]

    @router.get("/api/v1/users/me")
    def get_user(self, _: MockRequest) -> MockResponse:
        return MockResponse(content=USER_RESPONSE, status_code=200)

    @router.post("/security/api/v1/security-events")
    def send_itp_signal(self, _: MockRequest) -> MockResponse:
        status_code = self._product.get_status()
        return MockResponse(content={}, status_code=status_code)

    @router.delete(r"/api/v1/users/(?P<user_id>[^/]+)/sessions")
    def clear_user_sessions(self, request: MockRequest) -> MockResponse:
        """Mock the API endpoint for clearing a user's sessions."""
        match = re.search(
            r"/api/v1/users/(?P<user_id>[^/]+)/sessions", request.url.path
        )
        user_id = match.group("user_id") if match else None
        status_code = self._product.get_clear_user_sessions_status(user_id)
        return MockResponse(content={}, status_code=status_code)

    @router.get(r"/api/v1/users/(?P<user_id>[^/]+)$")
    def get_user_by_id(self, request: MockRequest) -> MockResponse:
        """Mock the API endpoint for getting a user by their ID."""
        match = re.search(r"/api/v1/users/(?P<user_id>[^/]+)$", request.url.path)
        user_id = match.group("user_id") if match else None
        status, data = (
            self._product.get_get_user_response(user_id)
            if user_id
            else (HTTPStatus.NOT_FOUND, None)
        )
        return MockResponse(content=data, status_code=status)
