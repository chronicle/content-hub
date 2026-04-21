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

import json
from collections.abc import Iterable

from ..common import FAILURE_AUTH_RESPONSE, SUCCESS_INFO_RESPONSE

from open_search.tests.core.product import OpenSearchProduct
from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction


class OpenSearchSession(MockSession[MockRequest, MockResponse, OpenSearchProduct]):
    """
    A mock session that uses a router to simulate the OpenSearch REST API.
    """

    def get_routed_functions(self) -> Iterable[RouteFunction]:
        """Returns a list of all routed functions for the mock session."""
        return [self.get_info, self.post_search]

    @router.get(r".*")
    def get_info(self, request: MockRequest) -> MockResponse:
        """Handles the `client.info()` call, which makes a GET request to /."""
        # Simulate an authentication failure based on the host
        if "invalid-host" in request.url.netloc:
            return MockResponse(
                content=json.dumps(FAILURE_AUTH_RESPONSE), status_code=401
            )

        # On success, return the standard info response
        return MockResponse(content=json.dumps(SUCCESS_INFO_RESPONSE), status_code=200)

    @router.post(r"/(?P<index_name>.*)/_search")
    def post_search(self, _request: MockRequest) -> MockResponse:
        """
        Handles the `client.search()` call, which makes a POST request to
        /<index_name>/_search.
        """
        return MockResponse(
            content=json.dumps(self._product.get_search_results()), status_code=200
        )
