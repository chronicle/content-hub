from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import requests

from huntbase.core import constants
from huntbase.core.huntbase_exceptions import (
    HuntbaseApiError,
    HuntbaseAuthError,
    HuntbaseConfigurationError,
    HuntbaseConnectionError,
    HuntbaseNotFoundError,
    HuntbasePermissionError,
    HuntbaseRateLimitError,
)
from huntbase.core.huntbase_manager import HuntbaseManager, app_root_from_api_root, normalize_api_root

from .. import common

if TYPE_CHECKING:
    from ..core.product import Huntbase
    from ..core.session import HuntbaseSession


def test_normalize_api_root_adds_prefix() -> None:
    assert normalize_api_root("https://hb.example.com/") == "https://hb.example.com/api/v1"
    assert normalize_api_root("https://hb.example.com/api/v1/") == "https://hb.example.com/api/v1"
    assert app_root_from_api_root("https://hb.example.com/api/v1") == "https://hb.example.com"


@pytest.mark.parametrize("root", ["", "hb.example.com", "ftp://hb.example.com"])
def test_normalize_api_root_rejects_bad_values(root: str) -> None:
    with pytest.raises(HuntbaseConfigurationError):
        normalize_api_root(root)


def test_empty_key_rejected(script_session: HuntbaseSession) -> None:
    with pytest.raises(HuntbaseConfigurationError):
        HuntbaseManager(common.API_ROOT, " ", session=script_session)


def test_headers_and_ssl(script_session: HuntbaseSession) -> None:
    manager = HuntbaseManager(common.API_ROOT, "hb_pat_x", verify_ssl=False, session=script_session)
    assert script_session.headers["Authorization"] == "Bearer hb_pat_x"
    assert script_session.headers["User-Agent"] == constants.USER_AGENT
    assert script_session.verify is False
    assert "hb_pat_x" not in repr(manager.__dict__.get("api_root"))


def test_retries_on_429_then_succeeds(
    manager: HuntbaseManager, huntbase: Huntbase, script_session: HuntbaseSession, no_retry_sleep: list[float]
) -> None:
    huntbase.fail("ping", 429, times=2, headers={"Retry-After": "7"})
    manager.ping()
    assert len(script_session.request_history) == 3
    assert no_retry_sleep == [7.0, 7.0]


def test_retries_on_503_with_backoff(manager: HuntbaseManager, huntbase: Huntbase, no_retry_sleep: list[float]) -> None:
    huntbase.fail("ping", 503, times=1)
    manager.ping()
    assert no_retry_sleep == [constants.RETRY_BACKOFF_SECONDS]


def test_gives_up_after_max_retries(
    manager: HuntbaseManager, huntbase: Huntbase, script_session: HuntbaseSession
) -> None:
    huntbase.fail("ping", 429, times=10)
    with pytest.raises(HuntbaseRateLimitError):
        manager.ping()
    assert len(script_session.request_history) == constants.MAX_RETRIES + 1


def test_server_error_after_retries(manager: HuntbaseManager, huntbase: Huntbase) -> None:
    huntbase.fail("ping", 502, times=10, body={"detail": "upstream down"})
    with pytest.raises(HuntbaseApiError, match="502.*upstream down"):
        manager.ping()


@pytest.mark.parametrize(
    ("status", "error", "text"),
    [
        (401, HuntbaseAuthError, "rejected the API key"),
        (403, HuntbasePermissionError, "not allowed"),
        (402, HuntbasePermissionError, "plan does not include"),
        (404, HuntbaseNotFoundError, "Not found"),
        (422, HuntbaseApiError, "returned 422"),
    ],
)
def test_error_mapping(manager: HuntbaseManager, huntbase: Huntbase, status: int, error: type, text: str) -> None:
    huntbase.fail("ping", status, body={"status": status, "title": "x", "detail": "problem detail"})
    with pytest.raises(error, match=text) as caught:
        manager.ping()
    assert caught.value.status_code == status
    assert "hb_pat_test_key" not in str(caught.value)


def test_fastapi_validation_detail(manager: HuntbaseManager, huntbase: Huntbase) -> None:
    huntbase.fail("ping", 400, body={"detail": [{"msg": "field required"}, {"msg": "bad type"}]})
    with pytest.raises(HuntbaseApiError, match="field required; bad type"):
        manager.ping()


def test_connection_error_retried_then_raised(
    manager: HuntbaseManager, monkeypatch: pytest.MonkeyPatch, no_retry_sleep: list[float]
) -> None:
    def boom(*_: object, **__: object) -> None:
        raise requests.ConnectionError("refused")

    monkeypatch.setattr(manager.session, "request", boom)
    with pytest.raises(HuntbaseConnectionError, match="Could not reach Huntbase"):
        manager.ping()
    assert len(no_retry_sleep) == constants.MAX_RETRIES


def test_lookup_indicators_batches_and_links(
    manager: HuntbaseManager, huntbase: Huntbase, script_session: HuntbaseSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(constants, "INTEL_LOOKUP_BATCH_SIZE", 2)
    huntbase.add_indicator("1.2.3.4", id="ind-1")
    results = manager.lookup_indicators(["1.2.3.4", "5.6.7.8", "evil.example", "1.2.3.4"])
    assert [r.input for r in results] == ["1.2.3.4", "5.6.7.8", "evil.example"]
    assert len(script_session.request_history) == 2
    assert results[0].is_known
    assert results[0].url == f"{common.APP_ROOT}/intelligence/indicators/ind-1?src=google_secops"
    assert results[1].url is None


def test_find_entities(manager: HuntbaseManager, huntbase: Huntbase, script_session: HuntbaseSession) -> None:
    huntbase.entities = [{"id": "e1", "type": "device", "tags": ["finance"], "attributes": {"name": "ws-0142"}}]
    matches = manager.find_entities("WS-0142", entity_type="device")
    assert matches[0].entity_id == "e1"
    assert matches[0].url.endswith("/entities/e1?src=google_secops")
    assert matches[0].enrichment()["tags"] == "finance"
    params = dict(script_session.request_history[0].request.kwargs["params"])
    assert params == {
        "value": "WS-0142",
        "include": "summary",
        "limit": constants.ENTITY_SEARCH_LIMIT,
        "entity_type": "device",
    }


def test_start_hunt_body(manager: HuntbaseManager, huntbase: Huntbase) -> None:
    hunt = manager.start_hunt(
        [{"type": "ip", "value": "1.2.3.4"}],
        title="T",
        hypothesis="H",
        severity="high",
        external_ref={"source": "google_secops", "id": "7", "url": "https://secops.example/cases/7"},
        reuse_open=True,
    )
    assert hunt.hunt_id == "hunt-new-1"
    assert hunt.status == "accepted"
    assert hunt.url == "https://huntbase.example.com/hunts/hunt-new-1?org=o1&src=api"
    assert huntbase.started_hunts[0] == {
        "seed_values": [{"type": "ip", "value": "1.2.3.4"}],
        "session_mode": "supervised",
        "title": "T",
        "hypothesis": "H",
        "severity": "high",
        "external_ref": {"source": "google_secops", "id": "7", "url": "https://secops.example/cases/7"},
        "reuse_open": True,
    }


def test_start_hunt_reuse_open_needs_case_url(manager: HuntbaseManager, huntbase: Huntbase) -> None:
    manager.start_hunt(
        [{"type": "ip", "value": "1.2.3.4"}], external_ref={"source": "google_secops", "id": "7"}, reuse_open=True
    )
    manager.start_hunt([{"type": "ip", "value": "1.2.3.4"}], reuse_open=True)
    assert "reuse_open" not in huntbase.started_hunts[0]
    assert "reuse_open" not in huntbase.started_hunts[1]


def test_start_hunt_needs_seeds(manager: HuntbaseManager) -> None:
    with pytest.raises(HuntbaseConfigurationError):
        manager.start_hunt([])


def test_get_hunt_not_found(manager: HuntbaseManager) -> None:
    with pytest.raises(HuntbaseNotFoundError, match="Session not found"):
        manager.get_hunt("missing")


def test_list_findings_params(manager: HuntbaseManager, huntbase: Huntbase, script_session: HuntbaseSession) -> None:
    huntbase.findings = [
        {"id": "f1", "title": "A", "disposition": "confirmed", "created_at": "2026-11-21T10:00:00Z"},
        {"id": "f2", "title": "B", "disposition": "benign", "created_at": "2026-11-21T11:00:00Z"},
    ]
    findings = manager.list_findings("2026-11-21T00:00:00Z", ["confirmed"])
    assert [f.finding_id for f in findings] == ["f1"]
    assert findings[0].url.endswith("/findings/f1?src=google_secops")
    params = dict(script_session.request_history[0].request.kwargs["params"])
    assert params["since"] == "2026-11-21T00:00:00Z"
    assert params["disposition"] == "confirmed"


def test_list_insights_bare_list(manager: HuntbaseManager, huntbase: Huntbase, script_session: HuntbaseSession) -> None:
    huntbase.insights = [{"event_id": "i1", "message": "M", "severity": "High", "time": "2026-11-21T10:00:00Z"}]
    insights = manager.list_insights("2026-11-21T00:00:00Z", "high")
    assert insights[0].insight_id == "i1"
    assert insights[0].url.endswith("/insights/i1?src=google_secops")
    params = dict(script_session.request_history[0].request.kwargs["params"])
    assert params["severity"] == "High"
    assert params["from"] == "2026-11-21T00:00:00Z"
    assert params["order"] == "asc"


def test_scout_job_roundtrip(manager: HuntbaseManager, huntbase: Huntbase) -> None:
    huntbase.add_scout_job("job_1", {"state": "running"}, {"state": "succeeded", "answer": "42"})
    ref = {"source": "google_secops", "id": "1"}
    job = manager.ask_scout("why?", hunt_id="h1", external_ref=ref, initiative="low")
    assert job.job_id == "job_1"
    assert not job.is_done
    assert huntbase.scout_questions[0] == {
        "question": "why?",
        "hunt_id": "h1",
        "initiative": "low",
        "external_ref": ref,
    }
    job = manager.get_scout_job("job_1")
    assert job.is_done
    assert job.answer == "42"


def test_find_watchlist_by_name_or_id(manager: HuntbaseManager, huntbase: Huntbase) -> None:
    huntbase.watchlists = [{"id": "w1", "name": "SecOps escalations"}]
    assert manager.find_watchlist("secops ESCALATIONS").watchlist_id == "w1"
    assert manager.find_watchlist("w1").name == "SecOps escalations"
    with pytest.raises(HuntbaseNotFoundError, match="Available watch lists: SecOps escalations"):
        manager.find_watchlist("nope")


def test_pending_approvals_links(manager: HuntbaseManager, huntbase: Huntbase) -> None:
    huntbase.proposals = [{"proposal_id": "p1", "summary": "Add values", "state": "pending_approval", "action": "x"}]
    proposals = manager.list_pending_approvals(limit=5)
    assert proposals[0].title == "Add values"
    assert proposals[0].status == "pending_approval"
    assert proposals[0].url == f"{common.APP_ROOT}/needs-you?lane=approvals&proposal=p1&src=google_secops"
