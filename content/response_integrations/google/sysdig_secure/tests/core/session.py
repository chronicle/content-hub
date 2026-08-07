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

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction
from integration_testing.common import get_def_file_content

MOCK_DATA_PATH = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)


class ApiSession(
    MockSession[MockRequest, MockResponse, None]
):

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.test_connectivity
        ]

    @router.get("/secure/events/v1/events")
    def test_connectivity(self, _: MockRequest) -> MockResponse:
        return MockResponse(MOCK_DATA["test_connectivity_success"])
