"""Behaviour tests for the Alerts Connector fetch loop.

Each helper call is one connector iteration. ``state`` carries the saved
timestamp and alert id cache between iterations, the way the platform does, so
tests can assert on resume behaviour.
"""

from __future__ import annotations

from typing import Any

import pytest

from ...connectors import AlertsConnector
from ..common import (
    DEFAULT_PARAMETERS,
    HOUR_MS,
    NOW_MS,
    FakeManager,
    FakeSiemplify,
    build_alert_row,
)


def run_connector(
    monkeypatch: pytest.MonkeyPatch,
    rows: list[dict[str, Any]],
    state: dict[str, Any],
    parameters: dict[str, Any] | None = None,
    timing_out: bool = False,
) -> tuple[FakeSiemplify, FakeManager]:
    """Run a single connector iteration against canned alert rows."""
    params = dict(DEFAULT_PARAMETERS)
    if parameters:
        params.update(parameters)

    siemplify = FakeSiemplify(params, state)
    manager = FakeManager(rows)

    monkeypatch.setattr(AlertsConnector, "SiemplifyConnectorExecution", lambda: siemplify)
    monkeypatch.setattr(AlertsConnector, "OrcaSecurityManager", lambda **kwargs: manager)
    monkeypatch.setattr(AlertsConnector, "unix_now", lambda: NOW_MS)
    monkeypatch.setattr(AlertsConnector, "connector_starting_time", NOW_MS)
    monkeypatch.setattr(
        AlertsConnector, "is_approaching_timeout", lambda *args, **kwargs: timing_out
    )
    monkeypatch.setattr(
        AlertsConnector, "is_overflowed", lambda *args, **kwargs: False
    )
    monkeypatch.setattr(
        AlertsConnector, "read_ids", lambda *args, **kwargs: list(state.get("ids", []))
    )

    def write_ids(_siemplify, ids, stored_ids_limit=1000, **kwargs):
        state["ids"] = list(ids)[-stored_ids_limit:]
        state["stored_ids_limit"] = stored_ids_limit

    monkeypatch.setattr(AlertsConnector, "write_ids", write_ids)
    monkeypatch.setattr(
        AlertsConnector,
        "GetEnvironmentCommonFactory",
        lambda: type(
            "Factory",
            (),
            {
                "create_environment_manager": lambda *a, **k: type(
                    "Env", (), {"get_environment": lambda *a, **k: "Default"}
                )()
            },
        )(),
    )

    AlertsConnector.main(False)
    return siemplify, manager


def ingested_ids(siemplify: FakeSiemplify) -> list[str]:
    return [alert.ticket_id for alert in siemplify.returned_alerts]


def test_ingests_new_alerts_and_saves_last_sync_watermark(monkeypatch):
    rows = [
        build_alert_row("orca-1", NOW_MS - 2 * HOUR_MS, NOW_MS - 2 * HOUR_MS),
        build_alert_row("orca-2", NOW_MS - 2 * HOUR_MS, NOW_MS - HOUR_MS),
    ]
    state: dict[str, Any] = {}

    siemplify, _ = run_connector(monkeypatch, rows, state)

    assert ingested_ids(siemplify) == ["orca-1", "orca-2"]
    assert state["timestamp"] == NOW_MS - HOUR_MS


def test_second_run_dedupes_and_still_advances_the_watermark(monkeypatch):
    rows = [
        build_alert_row("orca-1", NOW_MS - 2 * HOUR_MS, NOW_MS - 2 * HOUR_MS),
        build_alert_row("orca-2", NOW_MS - 2 * HOUR_MS, NOW_MS - HOUR_MS),
    ]
    state: dict[str, Any] = {}

    run_connector(monkeypatch, rows, state)
    first_watermark = state["timestamp"]
    siemplify, _ = run_connector(monkeypatch, rows, state)

    assert ingested_ids(siemplify) == []
    # progress must not depend on finding new alerts, otherwise a window full of
    # already-seen alerts stalls the connector permanently
    assert state["timestamp"] >= first_watermark


def test_alert_that_becomes_eligible_after_creation_is_ingested(monkeypatch):
    """The bug: score populated after the watermark passed the alert's CreatedAt."""
    state: dict[str, Any] = {}
    late = build_alert_row(
        "orca-late", NOW_MS - 2 * HOUR_MS, NOW_MS - 2 * HOUR_MS, orca_score=1.0
    )
    other = build_alert_row(
        "orca-other", NOW_MS - HOUR_MS, NOW_MS - HOUR_MS, orca_score=9.0
    )
    parameters = {"Lowest Orca Score To Fetch": "9"}

    siemplify, _ = run_connector(monkeypatch, [late, other], state, parameters)
    assert ingested_ids(siemplify) == ["orca-other"]

    # the alert is rescored and its row rewritten, so last_sync moves forward
    late["data"]["OrcaScore"]["value"] = 9.0
    late["data"]["last_sync"] = build_alert_row(
        "x", 0, NOW_MS - 30 * 60 * 1000
    )["data"]["last_sync"]

    siemplify, _ = run_connector(monkeypatch, [late, other], state, parameters)
    assert ingested_ids(siemplify) == ["orca-late"]


def test_alerts_sharing_one_last_sync_second_are_all_delivered(monkeypatch):
    """A tie block bigger than a page must not stall the cursor."""
    tied_last_sync = NOW_MS - 2 * HOUR_MS
    rows = [
        build_alert_row(f"orca-tie-{index}", NOW_MS - 2 * HOUR_MS, tied_last_sync)
        for index in range(12)
    ]
    state: dict[str, Any] = {}
    parameters = {"Max Alerts To Fetch": "5"}

    delivered: list[str] = []
    for _ in range(10):
        siemplify, manager = run_connector(monkeypatch, rows, state, parameters)
        batch = ingested_ids(siemplify)
        delivered.extend(batch)
        if not batch:
            break

    assert sorted(delivered) == sorted(row["data"]["AlertId"]["value"] for row in rows)
    assert len(delivered) == len(set(delivered)), "no alert may be ingested twice"


def test_offset_paging_is_used_inside_a_tied_cursor(monkeypatch):
    tied_last_sync = NOW_MS - 2 * HOUR_MS
    rows = [
        build_alert_row(f"orca-tie-{index}", NOW_MS - 2 * HOUR_MS, tied_last_sync)
        for index in range(12)
    ]

    state: dict[str, Any] = {}
    parameters = {"Max Alerts To Fetch": "5"}
    offsets: list[int] = []

    # The first iteration fills its per-cycle quota from the first page, so paging
    # deeper into the tie happens once the leading rows are already ingested.
    for _ in range(3):
        _, manager = run_connector(monkeypatch, rows, state, parameters)
        offsets.extend(call["start_at_index"] for call in manager.calls)

    # the cursor cannot advance within the tied second, so the connector must
    # page with start_at_index instead of skipping the remaining rows
    assert max(offsets) > 0


def test_updates_to_alerts_older_than_the_lookback_are_ignored(monkeypatch):
    old = build_alert_row("orca-old", NOW_MS - 30 * HOUR_MS, NOW_MS - 20 * HOUR_MS)
    fresh = build_alert_row("orca-fresh", NOW_MS - HOUR_MS, NOW_MS - HOUR_MS)
    state: dict[str, Any] = {}

    siemplify, _ = run_connector(monkeypatch, [old, fresh], state)
    assert "orca-old" not in ingested_ids(siemplify)

    # the old alert's row is rewritten (for example a status change)
    old["data"]["last_sync"] = build_alert_row(
        "x", 0, NOW_MS - 10 * 60 * 1000
    )["data"]["last_sync"]

    siemplify, _ = run_connector(monkeypatch, [old, fresh], state)
    assert "orca-old" not in ingested_ids(siemplify)


def test_first_run_honours_max_hours_backwards(monkeypatch):
    """The lookback bound must not shrink the initial backfill window."""
    rows = [build_alert_row("orca-1", NOW_MS - 10 * HOUR_MS, NOW_MS - 10 * HOUR_MS)]

    siemplify, manager = run_connector(
        monkeypatch, rows, {}, {"Max Hours Backwards": "24"}
    )

    assert manager.calls[0]["start_timestamp"] == NOW_MS - 24 * HOUR_MS
    assert ingested_ids(siemplify) == ["orca-1"]


def test_resumed_run_clamps_the_cursor_to_the_lookback(monkeypatch):
    rows = [build_alert_row("orca-1", NOW_MS - HOUR_MS, NOW_MS - HOUR_MS)]
    stale = NOW_MS - 50 * HOUR_MS
    state: dict[str, Any] = {"timestamp": stale}

    _, manager = run_connector(monkeypatch, rows, state)

    # downtime longer than the lookback must not re-scan days of alerts
    assert manager.calls[0]["last_sync_start_timestamp"] > stale


def test_timeout_does_not_advance_the_watermark_past_unhandled_alerts(monkeypatch):
    rows = [
        build_alert_row(f"orca-{index}", NOW_MS - 2 * HOUR_MS, NOW_MS - 2 * HOUR_MS + index * 1000)
        for index in range(5)
    ]
    state: dict[str, Any] = {}

    siemplify, _ = run_connector(monkeypatch, rows, state, timing_out=True)
    assert ingested_ids(siemplify) == []
    assert "timestamp" not in state

    # the next healthy run picks all of them up exactly once
    siemplify, _ = run_connector(monkeypatch, rows, state)
    assert len(ingested_ids(siemplify)) == len(rows)


def test_id_cache_limit_is_raised_above_the_default(monkeypatch):
    rows = [build_alert_row("orca-1", NOW_MS - HOUR_MS, NOW_MS - HOUR_MS)]

    run_connector(monkeypatch, rows, {})

    assert AlertsConnector.STORED_IDS_LIMIT == 10000


def test_per_cycle_fetch_limit_is_respected(monkeypatch):
    rows = [
        build_alert_row(f"orca-{index}", NOW_MS - 2 * HOUR_MS, NOW_MS - 2 * HOUR_MS + index * 1000)
        for index in range(9)
    ]

    siemplify, _ = run_connector(monkeypatch, rows, {}, {"Max Alerts To Fetch": "4"})

    assert len(ingested_ids(siemplify)) == 4
