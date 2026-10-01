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

from collections.abc import Iterable
import copy

from TIPCommon.types import SingleJson
from .. import common
from .product import AzureApi
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class AzureApiSession(MockSession[MockRequest, MockResponse, AzureApi]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            get_oauth_token,
            self.get_users,
            self.get_users_post,
        ]

    @router.get("/v1.0/[a-zA-Z0-9-]+/users")
    def get_users(self, request: MockRequest) -> MockResponse:
        """Get users"""
        if (
            request.kwargs.get("headers")
            and "invalid/header" in request.kwargs.get("headers", {}).values()
        ):
            return MockResponse(
                status_code=400,
                content=common.INVALID_HEADER_RESPONSE,
            )
        return MockResponse(
            status_code=200,
            content=common.GET_USERS_RESPONSE,
        )

    @router.post("/v1.0/[a-zA-Z0-9-]+/users")
    def get_users_post(self, _: MockRequest) -> MockResponse:
        """Get users"""
        return MockResponse(
            status_code=200,
            content=common.GET_USERS_RESPONSE,
        )


@router.post("/[a-zA-Z0-9_-]+/oauth2/v2.0/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """Get an OAuth token"""
    if (
        common.INVALID_CLIENT_ID in request.kwargs["data"].values()
        or common.INVALID_CODE in request.kwargs["data"].values()
    ):
        return MockResponse(
            status_code=401,
            content=common.INVALID_TOKEN_RESPONSE,
        )
    content: SingleJson = copy.deepcopy(common.VALID_TOKEN_RESPONSE)
    if "code" in request.kwargs["data"]:
        content["refresh_token"] = "new_refresh_token"
        return MockResponse(
            status_code=200,
            content=content,
        )

    return MockResponse(
        status_code=200,
        content=content,
    )
