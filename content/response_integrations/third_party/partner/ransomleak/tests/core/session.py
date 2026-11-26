# Copyright 2026 RansomLeak
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

"""Routes the RansomLeak partner API endpoints to the in-memory tenant."""

from __future__ import annotations

import uuid
from typing import Iterable

from integration_testing import router
from integration_testing.common import get_request_payload
from integration_testing.request import MockRequest
from integration_testing.requests.response import MockResponse
from integration_testing.requests.session import MockSession, Response, RouteFunction

from ransomleak.tests.core.product import RansomLeak

PREFIX = "/api/integration"
UUID = r"[0-9a-fA-F-]{36}"


class RansomLeakSession(MockSession[MockRequest, MockResponse, RansomLeak]):
    """Mock HTTP session for the RansomLeak partner API."""

    def get_routed_functions(self) -> Iterable[RouteFunction[Response]]:
        return [
            self.health,
            self.grafana_health,
            self.list_users,
            self.user_analytics,
            self.user_risk,
            self.list_learning_paths,
            self.enroll,
            self.create_assignment,
            self.get_assignment,
            self.sdk_ok,
        ]

    def _authorized(self, request: MockRequest) -> bool:
        return request.headers.get("Authorization") == f"Bearer {self._product.api_key}"

    @staticmethod
    def _unauthorized() -> MockResponse:
        return MockResponse(content={"message": "Invalid API token", "code": "INVALID_API_TOKEN"}, status_code=401)

    @router.get(rf"{PREFIX}/health")
    def health(self, request: MockRequest) -> MockResponse:
        if not self._product.health_endpoint_available:
            return MockResponse(content={"message": "Cannot GET /api/integration/health"}, status_code=404)
        if not self._authorized(request):
            return self._unauthorized()
        return MockResponse(content={"status": "ok"})

    @router.get(rf"{PREFIX}/grafana/health")
    def grafana_health(self, request: MockRequest) -> MockResponse:
        if not self._authorized(request):
            return self._unauthorized()
        return MockResponse(content={"status": "ok"})

    @router.get(rf"{PREFIX}/users")
    def list_users(self, request: MockRequest) -> MockResponse:
        if not self._authorized(request):
            return self._unauthorized()
        email = get_request_payload(request).get("email")
        users = self._product.users
        if email:
            match = self._product.find_user(email)
            users = [match] if match else []
        return MockResponse(content=users, headers={"X-Total-Count": str(len(users))})

    @router.get(rf"{PREFIX}/users/{UUID}/analytics")
    def user_analytics(self, request: MockRequest) -> MockResponse:
        user_id = request.url.path.split("/")[-2]
        if user_id not in self._product.analytics:
            return MockResponse(content={"message": "User not found"}, status_code=404)
        return MockResponse(content=self._product.analytics[user_id])

    @router.get(rf"{PREFIX}/users/{UUID}/risk")
    def user_risk(self, request: MockRequest) -> MockResponse:
        user_id = request.url.path.split("/")[-2]
        if not self._product.risk_endpoint_available or user_id not in self._product.analytics:
            return MockResponse(content={"message": "Not Found"}, status_code=404)
        empty = {"score": None, "level": None, "confidence": None, "subScores": None, "computedAt": None}
        risk = self._product.risks.get(user_id, empty)
        return MockResponse(content={"userId": user_id, "riskScoringEnabled": True, **risk})

    @router.get(rf"{PREFIX}/learning-paths")
    def list_learning_paths(self, _: MockRequest) -> MockResponse:
        return MockResponse(content=self._product.learning_paths)

    @router.post(rf"{PREFIX}/learning-paths/{UUID}/enrollments")
    def enroll(self, request: MockRequest) -> MockResponse:
        learning_path_id = request.url.path.split("/")[-2]
        if not any(p["id"] == learning_path_id for p in self._product.learning_paths):
            return MockResponse(content={"message": "Learning path not found"}, status_code=404)
        body = get_request_payload(request)
        external_ids, emails = body.get("externalUserIds") or [], body.get("emails") or []
        if not external_ids and not emails:
            return MockResponse(
                content={"message": "Provide at least one of externalUserIds or emails"}, status_code=400
            )
        result = self._product.enroll(learning_path_id, external_ids, emails, body.get("dueDays"))
        return MockResponse(content=result, status_code=201)

    @router.post(rf"{PREFIX}/assignments")
    def create_assignment(self, request: MockRequest) -> MockResponse:
        body = get_request_payload(request)
        if body["exerciseSlug"] not in self._product.exercises:
            return MockResponse(content={"message": "Exercise not found"}, status_code=404)
        email = body["user"]["email"]
        if self._product.find_user(email) is None:
            return MockResponse(content={"message": "Assignee not found"}, status_code=404)
        for existing in self._product.assignments.values():
            if existing["idempotencyKey"] == body["idempotencyKey"]:
                return MockResponse(content=existing["response"], status_code=201)
        assignment_id = str(uuid.uuid4())
        response = {
            "assignmentId": assignment_id,
            "status": "pending",
            "exerciseSlug": body["exerciseSlug"],
            "userEmail": email,
            "deepLink": f"https://acme.ransomleak.com/a/{assignment_id}",
            "deepLinkExpiresAt": "2026-12-13T00:00:00.000Z",
            "createdAt": "2026-11-13T00:00:00.000Z",
        }
        self._product.assignments[assignment_id] = {"idempotencyKey": body["idempotencyKey"], "response": response}
        return MockResponse(content=response, status_code=201)

    @router.get(rf"{PREFIX}/assignments/{UUID}")
    def get_assignment(self, request: MockRequest) -> MockResponse:
        assignment = self._product.assignments.get(request.url.path.split("/")[-1])
        if assignment is None:
            return MockResponse(content={"message": "Assignment not found"}, status_code=404)
        response = {k: v for k, v in assignment["response"].items() if not k.startswith("deepLink")}
        return MockResponse(content=response)

    @router.post(r"/api/external/v1/sdk/.+")
    def sdk_ok(self, _: MockRequest) -> MockResponse:
        """Catch-all for the SDK's own platform calls (update entities, insights)."""
        return MockResponse(content={}, status_code=200)
