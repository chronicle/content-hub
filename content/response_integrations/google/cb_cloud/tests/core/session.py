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
import uuid

from integration_testing import router
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, RouteFunction
from integration_testing.common import get_def_file_content, get_request_payload

MOCK_DATA_PATH = pathlib.Path(__file__).parent / "mock_data.json"
MOCK_DATA = get_def_file_content(MOCK_DATA_PATH)


def check_auth(func):
    """Check authentication, return response if invalid."""
    def wrapper(self, request: MockRequest, **kwargs):
        """Inner wrapper."""
        auth_header = request.headers.get("X-Auth-Token")
        if "invalid" in auth_header:
            return MockResponse(
                content={
                    "error_code": "UNAUTHENTICATED",
                    "message": "Principal is not authenticated",
                    "id": "25ccb961-5e21-5e52-5c89-681b9e16dbe5"
                },
                status_code=401,
            )

        return func(self, request, **kwargs)
    return wrapper


class ApiSession(
    MockSession[MockRequest, MockResponse, None]
):

    def get_routed_functions(self) -> list[RouteFunction]:
        return [
            self.search_alerts,
            self.search_observations,
            self.search_observations_results,
            self.search_observation_details,
            self.search_observation_details_results,
        ]

    @router.post(r"/api/alerts/v7/orgs/\w+/alerts/_search")
    @check_auth
    def search_alerts(self, request: MockRequest) -> MockResponse:
        """Mock search alerts response."""
        json_data = get_request_payload(request, ["json"])
        alerts = self._product.list_alerts(json_data["start"], json_data["rows"])

        return MockResponse(
            content={"results": alerts}
        )

    @router.post(r"/api/investigate/v2/orgs/\w+/observations/search_jobs")
    @check_auth
    def search_observations(self, _: MockRequest) -> MockResponse:
        """Mock search observations response."""
        job_id = f"{uuid.uuid4()}-rmq"
        return MockResponse(
            content={"job_id": job_id}
        )

    @router.get(
        r"/api/investigate/v2/orgs/\w+/observations/search_jobs/(\w|-)+/results"
    )
    @check_auth
    def search_observations_results(self, _: MockRequest) -> MockResponse:
        """Mock search observations results response."""
        observations = self._product.list_observations()
        return MockResponse(
            content={
                "results": observations,
                "num_found": len(observations),
                "num_available": len(observations),
                "approximate_unaggregated": len(observations),
                "num_aggregated": len(observations),
                "contacted": 1,
                "completed": 1,
            }
        )

    @router.post(r"/api/investigate/v2/orgs/\w+/observations/detail_jobs")
    @check_auth
    def search_observation_details(self, _: MockRequest) -> MockResponse:
        """Mock search observations details response."""
        job_id = f"{uuid.uuid4()}-rmq"
        return MockResponse(
            content={"job_id": job_id}
        )

    @router.get(
        r"/api/investigate/v2/orgs/\w+/observations/detail_jobs/(\w|-)+/results"
    )
    @check_auth
    def search_observation_details_results(self, _: MockRequest) -> MockResponse:
        """Mock search observations details results response."""
        observations = self._product.list_observation_details()
        return MockResponse(
            content={
                "results": observations,
                "num_found": len(observations),
                "num_available": len(observations),
                "approximate_unaggregated": len(observations),
                "num_aggregated": len(observations),
                "contacted": 1,
                "completed": 1,
            }
        )
