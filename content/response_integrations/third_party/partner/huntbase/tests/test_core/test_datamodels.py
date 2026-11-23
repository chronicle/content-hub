from __future__ import annotations

import datetime

import pytest

from huntbase.core import constants
from huntbase.core.datamodels import (
    Finding,
    Hunt,
    IndicatorResult,
    Insight,
    ScoutJob,
    parse_timestamp,
    severity_rank,
    severity_to_priority,
    to_unix_ms,
)


def test_parse_timestamp_variants() -> None:
    expected = datetime.datetime(2026, 11, 21, 10, 0, tzinfo=datetime.UTC)
    assert parse_timestamp("2026-11-21T10:00:00Z") == expected
    assert parse_timestamp("2026-11-21T10:00:00") == expected
    assert parse_timestamp(expected.timestamp()) == expected
    assert parse_timestamp(expected.timestamp() * 1000) == expected
    assert parse_timestamp("garbage") is None
    assert parse_timestamp(None) is None
    assert to_unix_ms("2026-11-21T10:00:00Z") == int(expected.timestamp() * 1000)


@pytest.mark.parametrize(
    ("severity", "priority"),
    [("critical", 100), ("HIGH", 80), ("medium", 60), ("low", 40), ("informational", -1), (None, 60)],
)
def test_severity_to_priority(severity: str | None, priority: int) -> None:
    assert severity_to_priority(severity) == priority


def test_severity_rank() -> None:
    assert severity_rank("info") == 0
    assert severity_rank("critical") > severity_rank("high")
    assert severity_rank("weird") == -1


def test_indicator_suspicious_threshold() -> None:
    result = IndicatorResult.from_json({
        "input": "1.2.3.4",
        "status": "known",
        "best": {"effective_confidence": 75, "revoked": False},
    })
    assert result.is_suspicious(70)
    assert not result.is_suspicious(80)
    result.best["revoked"] = True
    assert not result.is_suspicious(10)
    assert not IndicatorResult.from_json({"input": "x", "status": "unknown"}).is_suspicious(0)


def test_hunt_finished_by_status_or_verdict() -> None:
    assert Hunt.from_json({"id": "h", "status": "concluded"}).is_finished
    assert Hunt.from_json({"id": "h", "status": "active", "latest_verdict": {"disposition": "benign"}}).is_finished
    draft = {"kind": "draft", "disposition": "benign"}
    assert not Hunt.from_json({"id": "h", "status": "active", "latest_verdict": draft}).is_finished
    hunt = Hunt.from_json({"hunt_session_id": "h2", "planning": "queued"})
    assert hunt.hunt_id == "h2"
    assert not hunt.is_finished
    hunt = Hunt.from_json({"id": "h", "status": "active", "latest_verdict": {"disposition": "benign", "reason": "S"}})
    assert hunt.verdict == "benign"
    assert hunt.summary == "S"


def test_finding_and_insight_parsing() -> None:
    finding = Finding.from_json({"id": "f", "session_id": "h", "entities": [{"type": "ip", "value": "1.1.1.1"}, "x"]})
    assert finding.hunt_id == "h"
    assert finding.entities == [{"type": "ip", "value": "1.1.1.1"}]
    insight = Insight.from_json({
        "event_id": "i",
        "message": "M",
        "evidences": [{"src_ip": "10.0.0.1", "device_hostname": "ws-1", "user": "alice"}, "skip"],
    })
    assert insight.entities() == [
        {"type": "ip", "value": "10.0.0.1"},
        {"type": "host", "value": "ws-1"},
        {"type": "user", "value": "alice"},
    ]


def test_scout_job_states() -> None:
    assert ScoutJob.from_json({"job_id": "j", "state": "succeeded"}).is_done
    assert ScoutJob.from_json({"job_id": "j", "status": "failed"}).is_failed
    for status in constants.SCOUT_TERMINAL_OK:
        assert ScoutJob.from_json({"status": status}).is_done
