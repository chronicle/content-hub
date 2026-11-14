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

from __future__ import annotations

import pytest

from ransomleak.core.exceptions import (
    RansomLeakAuthError,
    RansomLeakError,
    RansomLeakNotFoundError,
    RansomLeakValidationError,
)
from ransomleak.core.ransomleak_manager import RansomLeakManager, is_email
from ransomleak.tests.core.product import VALID_API_KEY, RansomLeak
from ransomleak.tests.core.session import RansomLeakSession

API_ROOT = "https://acme.ransomleak.com"
USER_ID = "3f1c2a9e-7b4d-4e2a-9c1f-0a1b2c3d4e5f"
LP_ID = "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def manager() -> RansomLeakManager:
    return RansomLeakManager(API_ROOT, VALID_API_KEY)


@pytest.fixture
def seeded(ransomleak: RansomLeak) -> RansomLeak:
    ransomleak.add_user(
        {"id": USER_ID, "email": "Jane.Doe@example.com", "firstName": "Jane", "lastName": "Doe", "externalId": "emp-1"},
        {"exercisesCompleted": 3, "exerciseHistory": []},
    )
    ransomleak.learning_paths.append({"id": LP_ID, "name": "Phishing Fundamentals", "description": None})
    ransomleak.exercises.add("phishing-introduction")
    return ransomleak


class TestConnectivity:
    def test_sends_bearer_key_to_authenticated_endpoint(
        self, manager: RansomLeakManager, script_session: RansomLeakSession
    ) -> None:
        assert manager.test_connectivity() is True
        request = script_session.request_history[-1].request
        assert request.url.path == "/api/integration/grafana/health"
        assert request.headers["Authorization"] == f"Bearer {VALID_API_KEY}"
        assert request.kwargs["timeout"] == 30

    def test_invalid_key_raises_auth_error(self) -> None:
        with pytest.raises(RansomLeakAuthError, match="HTTP 401"):
            RansomLeakManager(API_ROOT, "bad-key").test_connectivity()

    def test_api_root_trailing_slash_is_normalised(self, script_session: RansomLeakSession) -> None:
        RansomLeakManager(f"{API_ROOT}/", VALID_API_KEY).test_connectivity()
        assert script_session.request_history[-1].request.url.geturl() == f"{API_ROOT}/api/integration/grafana/health"


class TestUsers:
    def test_lookup_by_email_is_case_insensitive(self, manager: RansomLeakManager, seeded: RansomLeak) -> None:
        user = manager.get_user_by_email("jane.doe@EXAMPLE.com")
        assert user is not None
        assert user["id"] == USER_ID

    def test_lookup_sends_email_filter(
        self, manager: RansomLeakManager, seeded: RansomLeak, script_session: RansomLeakSession
    ) -> None:
        manager.get_user_by_email("jane.doe@example.com")
        assert script_session.request_history[-1].request.kwargs["params"] == {
            "email": "jane.doe@example.com",
            "limit": 1,
        }

    def test_unknown_email_returns_none(self, manager: RansomLeakManager, seeded: RansomLeak) -> None:
        assert manager.get_user_by_email("nobody@example.com") is None

    def test_invalid_email_rejected_locally(
        self, manager: RansomLeakManager, script_session: RansomLeakSession
    ) -> None:
        with pytest.raises(RansomLeakValidationError):
            manager.get_user_by_email("DOMAIN\\jdoe")
        assert script_session.request_history == []

    def test_analytics(self, manager: RansomLeakManager, seeded: RansomLeak) -> None:
        assert manager.get_user_analytics(USER_ID)["exercisesCompleted"] == 3

    def test_risk(self, manager: RansomLeakManager, seeded: RansomLeak) -> None:
        seeded.risks[USER_ID] = {"score": 58, "level": "high", "computedAt": "2026-11-14T03:00:00.000Z"}
        risk = manager.get_user_risk(USER_ID)
        assert risk["score"] == 58
        assert risk["level"] == "high"

    def test_risk_tolerates_older_backend(self, manager: RansomLeakManager, seeded: RansomLeak) -> None:
        seeded.risk_endpoint_available = False
        assert manager.get_user_risk(USER_ID) is None

    def test_is_email(self) -> None:
        assert is_email("a.b@example.co.uk")
        assert not is_email("jdoe")
        assert not is_email("")


class TestLearningPaths:
    def test_find_by_id_and_name(self, manager: RansomLeakManager, seeded: RansomLeak) -> None:
        assert manager.find_learning_path(LP_ID)["name"] == "Phishing Fundamentals"
        assert manager.find_learning_path("phishing fundamentals")["id"] == LP_ID
        assert manager.find_learning_path("missing") is None

    def test_enroll_by_email_returns_per_user_results(
        self, manager: RansomLeakManager, seeded: RansomLeak, script_session: RansomLeakSession
    ) -> None:
        result = manager.enroll_learning_path(LP_ID, emails=["JANE.doe@example.com", "ghost@example.com"], due_days=14)
        body = script_session.request_history[-1].request.kwargs["json"]
        assert body == {"emails": ["jane.doe@example.com", "ghost@example.com"], "dueDays": 14}
        assert result["assigned"] == 1
        assert result["notFound"] == ["ghost@example.com"]
        assert result["results"] == [
            {
                "email": "jane.doe@example.com",
                "userId": USER_ID,
                "status": "enrolled",
                "enrollmentId": f"enr-{USER_ID}",
            },
            {"email": "ghost@example.com", "status": "not_found"},
        ]
        again = manager.enroll_learning_path(LP_ID, emails=["jane.doe@example.com"])
        assert again["results"][0]["status"] == "already_enrolled"

    def test_enroll_still_accepts_external_ids(self, manager: RansomLeakManager, seeded: RansomLeak) -> None:
        result = manager.enroll_learning_path(LP_ID, external_user_ids=["emp-1", "ghost"])
        assert result["assigned"] == 1
        assert result["notFound"] == ["ghost"]

    @pytest.mark.parametrize("due_days", [0, 366])
    def test_enroll_rejects_out_of_range_due_days(self, manager: RansomLeakManager, due_days: int) -> None:
        with pytest.raises(RansomLeakValidationError):
            manager.enroll_learning_path(LP_ID, emails=["jane.doe@example.com"], due_days=due_days)

    def test_enroll_requires_users(self, manager: RansomLeakManager) -> None:
        with pytest.raises(RansomLeakValidationError):
            manager.enroll_learning_path(LP_ID, emails=[])

    def test_unknown_learning_path_raises_not_found(self, manager: RansomLeakManager, seeded: RansomLeak) -> None:
        with pytest.raises(RansomLeakNotFoundError):
            manager.enroll_learning_path("00000000-0000-0000-0000-000000000000", emails=["jane.doe@example.com"])


class TestAssignments:
    def test_create_is_idempotent_and_status_omits_deep_link(
        self, manager: RansomLeakManager, seeded: RansomLeak
    ) -> None:
        first = manager.create_assignment("phishing-introduction", "jane.doe@example.com", "key-1", reference="42")
        again = manager.create_assignment("phishing-introduction", "jane.doe@example.com", "key-1")
        assert first["assignmentId"] == again["assignmentId"]
        assert first["deepLink"]
        status = manager.get_assignment(first["assignmentId"])
        assert status["status"] == "pending"
        assert "deepLink" not in status

    def test_create_sends_source_and_reference(
        self, manager: RansomLeakManager, seeded: RansomLeak, script_session: RansomLeakSession
    ) -> None:
        manager.create_assignment("phishing-introduction", "jane.doe@example.com", "key-2", reference="42")
        body = script_session.request_history[-1].request.kwargs["json"]
        assert body == {
            "exerciseSlug": "phishing-introduction",
            "user": {"email": "jane.doe@example.com"},
            "idempotencyKey": "key-2",
            "source": "google_secops",
            "reference": "42",
        }

    def test_unknown_exercise_raises_not_found(self, manager: RansomLeakManager, seeded: RansomLeak) -> None:
        with pytest.raises(RansomLeakNotFoundError, match="Exercise not found"):
            manager.create_assignment("nope", "jane.doe@example.com", "key-3")


class TestErrors:
    def test_server_error_message_is_surfaced(
        self, monkeypatch: pytest.MonkeyPatch, manager: RansomLeakManager
    ) -> None:
        from integration_testing.requests.response import MockResponse

        monkeypatch.setattr(
            manager.session,
            "request",
            lambda *_, **__: MockResponse(content={"message": "boom"}, status_code=500),
        )
        with pytest.raises(RansomLeakError, match=r"HTTP 500\): boom"):
            manager.list_learning_paths()

    def test_timeout_is_wrapped(self, monkeypatch: pytest.MonkeyPatch, manager: RansomLeakManager) -> None:
        import requests

        def _timeout(*_: object, **__: object) -> None:
            raise requests.exceptions.Timeout

        monkeypatch.setattr(manager.session, "request", _timeout)
        with pytest.raises(RansomLeakError, match="timed out"):
            manager.test_connectivity()
