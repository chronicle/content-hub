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

from ransomleak.core.data_models import AssignmentRequest, EnrollmentCounts, RansomLeakConfig
from ransomleak.core.exceptions import (
    RansomLeakAuthError,
    RansomLeakError,
    RansomLeakNotFoundError,
    RansomLeakValidationError,
)
from ransomleak.core.ransomleak_manager import RansomLeakManager, validate_api_key, validate_api_root
from ransomleak.core.utils import is_email, map_concurrently
from ransomleak.tests.core.product import VALID_API_KEY, RansomLeak
from ransomleak.tests.core.session import RansomLeakSession

API_ROOT = "https://acme.ransomleak.com"
USER_ID = "3f1c2a9e-7b4d-4e2a-9c1f-0a1b2c3d4e5f"
LP_ID = "123e4567-e89b-12d3-a456-426614174000"


@pytest.fixture
def manager() -> RansomLeakManager:
    return RansomLeakManager(RansomLeakConfig(api_root=API_ROOT, api_key=VALID_API_KEY))


def _manager(api_root: str = API_ROOT, api_key: str = VALID_API_KEY) -> RansomLeakManager:
    return RansomLeakManager(RansomLeakConfig(api_root=api_root, api_key=api_key))


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
        assert request.url.path == "/api/integration/health"
        assert request.headers["Authorization"] == f"Bearer {VALID_API_KEY}"
        assert request.kwargs["timeout"] == 30

    def test_invalid_key_raises_auth_error(self) -> None:
        with pytest.raises(RansomLeakAuthError, match="HTTP 401"):
            _manager(api_key="bad-key").test_connectivity()

    def test_falls_back_to_grafana_health_on_older_backend(
        self, manager: RansomLeakManager, ransomleak: RansomLeak, script_session: RansomLeakSession
    ) -> None:
        ransomleak.health_endpoint_available = False
        assert manager.test_connectivity() is True
        assert script_session.request_history[-1].request.url.path == "/api/integration/grafana/health"

    def test_fallback_still_rejects_invalid_key(self, ransomleak: RansomLeak) -> None:
        ransomleak.health_endpoint_available = False
        with pytest.raises(RansomLeakAuthError, match="HTTP 401"):
            _manager(api_key="bad-key").test_connectivity()

    def test_api_root_trailing_slash_is_normalised(self, script_session: RansomLeakSession) -> None:
        _manager(f"{API_ROOT}/").test_connectivity()
        assert script_session.request_history[-1].request.url.geturl() == f"{API_ROOT}/api/integration/health"


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
        assert manager.find_learning_path(LP_ID).name == "Phishing Fundamentals"
        assert manager.find_learning_path("phishing fundamentals").id == LP_ID
        assert manager.find_learning_path("missing") is None

    def test_enroll_by_email_returns_per_user_results(
        self, manager: RansomLeakManager, seeded: RansomLeak, script_session: RansomLeakSession
    ) -> None:
        result = manager.enroll_learning_path(LP_ID, emails=["jane.doe@example.com", "ghost@example.com"], due_days=14)
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
        first = manager.create_assignment(
            AssignmentRequest("phishing-introduction", "jane.doe@example.com", "key-1", reference="42"),
        )
        again = manager.create_assignment(AssignmentRequest("phishing-introduction", "jane.doe@example.com", "key-1"))
        assert first.assignment_id
        assert first.assignment_id == again.assignment_id
        assert first.status == "pending"
        status = manager.get_assignment(first.assignment_id)
        assert status["status"] == "pending"
        assert "deepLink" not in status

    def test_create_sends_source_and_reference(
        self, manager: RansomLeakManager, seeded: RansomLeak, script_session: RansomLeakSession
    ) -> None:
        manager.create_assignment(
            AssignmentRequest("phishing-introduction", "jane.doe@example.com", "key-2", reference="42"),
        )
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
            manager.create_assignment(AssignmentRequest("nope", "jane.doe@example.com", "key-3"))


class TestErrors:
    def test_server_error_message_is_surfaced(
        self, monkeypatch: pytest.MonkeyPatch, manager: RansomLeakManager
    ) -> None:
        from integration_testing.requests.response import MockResponse

        monkeypatch.setattr(
            manager._get_or_create_session(),
            "get",
            lambda *_, **__: MockResponse(content={"message": "boom"}, status_code=500),
        )
        with pytest.raises(RansomLeakError, match=r"HTTP 500\): boom"):
            manager.list_learning_paths()

    def test_timeout_is_wrapped(self, monkeypatch: pytest.MonkeyPatch, manager: RansomLeakManager) -> None:
        import requests

        def _timeout(*_: object, **__: object) -> None:
            raise requests.exceptions.Timeout

        monkeypatch.setattr(manager._get_or_create_session(), "get", _timeout)
        with pytest.raises(RansomLeakError, match="timed out"):
            manager.test_connectivity()


class TestConfigValidation:
    @pytest.mark.parametrize(
        "api_root",
        [
            "http://acme.ransomleak.com",
            "ftp://acme.ransomleak.com",
            "acme.ransomleak.com",
            "https://",
            "https://localhost",
            "https://app.localhost:3001",
            "https://127.0.0.1",
            "https://[::1]",
            "https://[::ffff:127.0.0.1]",
            "https://0.0.0.0",
            "https://169.254.169.254/latest/meta-data",
            "https://[fd00:ec2::254]",
            "https://metadata.google.internal",
            "https://user:pass@acme.ransomleak.com",
            "https://token@acme.ransomleak.com",
            "https://acme.ransomleak.com/?x=1",
            "https://acme.ransomleak.com/#frag",
            "https://acme.ransomleak.com:notaport",
        ],
    )
    def test_rejects_unsafe_api_root(self, api_root: str) -> None:
        with pytest.raises(RansomLeakValidationError):
            validate_api_root(api_root)

    @pytest.mark.parametrize(
        ("api_root", "expected"),
        [
            (API_ROOT, f"{API_ROOT}/"),
            (f"  {API_ROOT}//  ", f"{API_ROOT}/"),
            ("https://training.example.com:8443/lms", "https://training.example.com:8443/lms/"),
        ],
    )
    def test_accepts_https_api_root(self, api_root: str, expected: str) -> None:
        assert validate_api_root(api_root) == expected

    def test_rejects_plain_http_before_any_request(self, script_session: RansomLeakSession) -> None:
        with pytest.raises(RansomLeakValidationError, match="https"):
            _manager("http://acme.ransomleak.com")
        assert script_session.request_history == []

    def test_api_key_is_stripped(self, script_session: RansomLeakSession) -> None:
        _manager(api_key=f"  {VALID_API_KEY}\n").test_connectivity()
        assert validate_api_key(f"  {VALID_API_KEY}  ") == VALID_API_KEY
        assert script_session.request_history[-1].request.headers["Authorization"] == f"Bearer {VALID_API_KEY}"

    @pytest.mark.parametrize("api_key", ["", "   ", "abc\r\nX-Injected: 1", "abc\ndef"])
    def test_rejects_empty_or_multiline_api_key(self, api_key: str) -> None:
        with pytest.raises(RansomLeakValidationError):
            _manager(api_key=api_key)


class TestPathEncoding:
    @pytest.mark.parametrize("user_id", ["../../learning-paths", "a/b", "x?limit=1000", "y#z", "a b"])
    def test_path_params_are_percent_encoded(self, manager: RansomLeakManager, user_id: str) -> None:
        url = manager._url("user_analytics", {"user_id": user_id})
        path = url.removeprefix(f"{API_ROOT}/api/integration/users/").removesuffix("/analytics")
        assert "/" not in path
        assert "?" not in url
        assert "#" not in url
        assert url.endswith("/analytics")

    def test_traversal_id_does_not_leave_the_user_route(
        self, monkeypatch: pytest.MonkeyPatch, manager: RansomLeakManager
    ) -> None:
        from integration_testing.requests.response import MockResponse

        urls: list[str] = []

        def _capture(url: str, **_: object) -> MockResponse:
            urls.append(url)
            return MockResponse(content={})

        monkeypatch.setattr(manager._get_or_create_session(), "get", _capture)
        manager.get_user_analytics("../../learning-paths")
        assert urls == [f"{API_ROOT}/api/integration/users/..%2F..%2Flearning-paths/analytics"]


class TestSessions:
    def test_get_retries_only_idempotent_reads(self, manager: RansomLeakManager) -> None:
        session = manager._get_or_create_session()
        retry = session.get_adapter(f"{API_ROOT}/").max_retries
        assert session is manager._get_or_create_session()
        assert retry.total == 3
        assert set(retry.status_forcelist) == {429, 502, 503, 504}
        assert retry.allowed_methods == frozenset({"GET"})

    def test_close_closes_every_tracked_session(
        self, monkeypatch: pytest.MonkeyPatch, manager: RansomLeakManager
    ) -> None:
        closed: list[object] = []
        session = manager._get_or_create_session()
        monkeypatch.setattr(session, "close", lambda: closed.append(session))
        map_concurrently(lambda _: manager._get_or_create_session(), ["a", "b", "c"])
        tracked = len(manager._sessions)
        assert tracked >= 1
        manager.close()
        assert closed
        assert manager._sessions == []

    def test_empty_responses_are_coerced_to_empty_dict(
        self, monkeypatch: pytest.MonkeyPatch, manager: RansomLeakManager
    ) -> None:
        from integration_testing.requests.response import MockResponse

        session = manager._get_or_create_session()
        monkeypatch.setattr(session, "get", lambda *_, **__: MockResponse(content=None, status_code=204))
        monkeypatch.setattr(session, "post", lambda *_, **__: MockResponse(content=None, status_code=204))
        assert manager.get_user_analytics(USER_ID) == {}
        assert manager.get_assignment(USER_ID) == {}
        assert manager.enroll_learning_path(LP_ID, emails=["jane.doe@example.com"]) == {}
        assert manager.create_assignment(AssignmentRequest("x", "jane.doe@example.com", "k")).assignment_id is None


class TestEnrollmentCounts:
    def test_null_counters_become_zero(self) -> None:
        counts = EnrollmentCounts.from_json({"assigned": None, "alreadyEnrolled": None})
        assert counts == EnrollmentCounts(0, 0, 0)
        total = counts + EnrollmentCounts.from_json({"assigned": 2, "skippedUnlicensed": 1})
        assert total.to_json() == {"assigned": 2, "already_enrolled": 0, "skipped_unlicensed": 1}
