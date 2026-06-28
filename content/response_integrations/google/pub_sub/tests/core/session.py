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

from pub_sub.tests.core.product import Product

MOCK_DATA_PATH = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)


class ApiSession(
    MockSession[MockRequest, MockResponse, Product]
):

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.get_sub,
            self.create_sub,
            self.get_topic,
            self.pull_messages,
            self.ack_messages,
            self.get_access_token_invalid,
            self.get_access_token,
            self.get_default_service_account,
            self.get_default_service_account_email,
            self.get_service_account_token,
            self.get_oauth_token,
        ]

    @router.get(
        "/v1/projects/test-project/subscriptions/([a-zA-Z]|-|_)+"
    )
    def get_sub(self, request: MockRequest) -> MockResponse:
        """Mock get sub request."""
        if "soar_pub_sub" in request.url.path:
            return MockResponse(**MOCK_DATA["subscription_not_found"])
        return MockResponse(**MOCK_DATA["subscription"])

    @router.put(
        "/v1/projects/test-project/subscriptions/([a-zA-Z]|-|_)+"
    )
    def create_sub(self, _: MockRequest) -> MockResponse:
        return MockResponse(**MOCK_DATA["subscription"])

    @router.get(
        "/v1/projects/test-project/topics/([a-zA-Z]|-|_)+"
    )
    def get_topic(self, _: MockRequest) -> MockResponse:
        return MockResponse(**MOCK_DATA["topic"])

    @router.post(
        "/v1/projects/test-project/subscriptions/([a-zA-Z]|-|_)+:pull"
    )
    def pull_messages(self, _: MockRequest) -> MockResponse:
        return MockResponse({
            "receivedMessages": self._product.list_messages()
        })

    @router.post(
        "/v1/projects/test-project/subscriptions/([a-zA-Z]|-|_)+:acknowledge"
    )
    def ack_messages(self, _: MockRequest) -> MockResponse:
        return MockResponse()

    @router.post(
        r"/v1/projects/-/serviceAccounts/invalid-sa@domain.com:generateAccessToken"
    )
    def get_access_token_invalid(self, _: MockRequest) -> MockResponse:
        return MockResponse(**MOCK_DATA["get_access_token_invalid"])

    @router.post(
        r"/v1/projects/-/serviceAccounts/"
        r"(\w|-)+@([a-zA-Z]|-|\.)+com:generateAccessToken"
    )
    def get_access_token(self, _: MockRequest) -> MockResponse:
        """Mock get access token request."""
        return MockResponse(
            content={
                "accessToken": "xxxx.yyyy",
                "expireTime": (
                    datetime.datetime.now() + datetime.timedelta(seconds=3600)
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
        )

    @router.get(r"/computeMetadata/v1/instance/service-accounts/default/?$")
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

    @router.get(r"/computeMetadata/v1/instance/service-accounts/default/email")
    def get_default_service_account_email(self, _: MockRequest) -> MockResponse:
        return MockResponse(
            content="default@domain.com",
            headers={
                "content-type": "text/plain"
            }
        )

    @router.get(
        r"/computeMetadata/v1/instance/service-accounts/"
        r"(\w|-)+@([a-zA-Z]|-|\.)+\.com/token"
    )
    def get_service_account_token(self, _: MockRequest) -> MockResponse:
        """Mock get service account token request."""
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
