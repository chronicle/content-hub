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
from collections.abc import Iterable

from ...tests import common
from ...tests.core.product import AzureMonitor
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class AzureMonitorSession(MockSession[MockRequest, MockResponse, AzureMonitor]):
    def get_routed_functions(self) -> Iterable[RouteFunction]:
        return [
            self.search_logs,
            get_oauth_token,
        ]

    @router.post("/v1/workspaces/[a-zA-Z0-9_-]+/query")
    def search_logs(self, request: MockRequest) -> MockResponse:
        """Search logs mock implementation"""
        if "invalid_query" in request.kwargs["json"]["query"]:
            return MockResponse(status_code=200, content={})
        if "invalid_workspace_id" in request.url.path:
            return MockResponse(
                status_code=403, content={"error": {"message": "Invalid Workspace ID."}}
            )

        logs = self._product.get_logs(request.kwargs["json"]["query"])

        return MockResponse(
            status_code=200, content=common.azure_log_entries_to_api_json(logs)
        )


@router.post("/[a-zA-Z0-9_-]+/oauth2/token")
def get_oauth_token(request: MockRequest) -> MockResponse:
    """Get an OAuth token"""
    if "invalid_client_id" in request.kwargs["data"].values():
        return MockResponse(
            status_code=401,
            content={
                "error": "unauthorized_client",
                "error_description": "Invalid client id is provided.",
            },
        )

    return MockResponse(
        status_code=200,
        content=common.MOCK_DATA["oauth_token"],
    )
