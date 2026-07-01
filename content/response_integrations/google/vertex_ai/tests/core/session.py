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

import datetime
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
            self.count_tokens,
            self.generate_content,
            self.get_access_token_invalid,
            self.get_access_token,
            self.get_default_service_account,
            self.get_service_account_token,
            self.get_universe_domain,
            self.get_oauth_token,
            self.get_entity_data,
            self.get_publishers_model,
        ]

    @router.post(
        "/api/external/v1/entities/GetEntityData"
    )
    def get_entity_data(self, _: MockRequest) -> MockResponse:
        return MockResponse(**MOCK_DATA["get_entity_data"])

    @router.get(r"/v1/publishers/(.)+/models/(.)+")
    def get_publishers_model(self, _: MockRequest) -> MockResponse:
        return MockResponse(**MOCK_DATA["get_publishers_model"])

    @router.post(
        r"/v1/projects/(.)+/locations/(.)+/publishers/"
        r"(.)+/models/(.)+:countTokens"
    )
    def count_tokens(self, _: MockRequest) -> MockResponse:
        """Mock count tokens request."""
        return MockResponse({
            "totalTokens": 10,
            "totalBillableCharacters": 32
        })

    @router.post(
        r"/v1/projects/(.)+/locations/(.)+/publishers/"
        r"(.)+/models/(.)+:generateContent"
    )
    def generate_content(self, _: MockRequest) -> MockResponse:
        """Mock generate content request."""
        return MockResponse(**MOCK_DATA["generate_content"])

    @router.post(
        r"/v1/projects/-/serviceAccounts/invalid-sa@domain.com:generateAccessToken"
    )
    def get_access_token_invalid(self, _: MockRequest) -> MockResponse:
        return MockResponse(**MOCK_DATA["get_access_token_invalid"])

    @router.post(
        r"/v1/projects/-/serviceAccounts/\w+@[a-zA-Z]+\.com:generateAccessToken"
    )
    def get_access_token(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={
                "accessToken": "xxxx.yyyy",
                "expireTime": (
                    datetime.datetime.now() + datetime.timedelta(seconds=3600)
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        )

    @router.get("/computeMetadata/v1/universe/universe-domain")
    def get_universe_domain(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content="googleapis.com",
            headers={
                "content-type": "text/plain"
            }
        )

    @router.get("/computeMetadata/v1/instance/service-accounts/default/")
    def get_default_service_account(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content={
                "email": "default@domain.com",
                "scopes": ["test-scope"],
                "aliases": ["default"]
            },
            headers={
                "content-type": "application/json"
            }
        )

    @router.get(
        r"/computeMetadata/v1/instance/service-accounts/\w+@[a-zA-Z]+\.com/token"
    )
    def get_service_account_token(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            {
                "access_token": "xxxx.yyyy",
                "expires_in": 3599,
                "token_type": "Bearer"
            },
            headers={
                "content-type": "application/json"
            }
        )

    @router.post("/token")
    def get_oauth_token(self, _: MockRequest) -> MockResponse:
        """Get an OAuth token"""
        return MockResponse(
            {
                "access_token": "xxxx.yyyy",
                "expires_in": 3599,
                "token_type": "Bearer"
            }
        )
