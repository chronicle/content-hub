"""Pins the alert query contract the connector's cursor logic relies on."""

from __future__ import annotations

import datetime

from ...core.OrcaSecurityParser import OrcaSecurityParser
from ...core.query_builder import AlertQueryBuilder
from ..common import HOUR_MS, NOW_MS, build_alert_row, build_response, to_iso


def _conditions(payload):
    return {
        condition["key"]: condition
        for condition in payload["query"]["with"]["values"]
        if "key" in condition
    }


def test_last_sync_query_orders_by_last_sync_ascending():
    payload = AlertQueryBuilder(
        NOW_MS - 3 * HOUR_MS, 100, NOW_MS - HOUR_MS
    ).build()

    # The cursor is taken from the last row of a page, so ordering must be by
    # last_sync (ascending is the endpoint default for a bare order_by).
    assert payload["order_by[]"] == ["last_sync"]


def test_without_last_sync_cursor_falls_back_to_created_at_order():
    payload = AlertQueryBuilder(NOW_MS - 3 * HOUR_MS, 100).build()

    assert payload["order_by[]"] == ["CreatedAt"]


def test_time_filters_use_precise_range_operator_with_iso_values():
    payload = AlertQueryBuilder(
        NOW_MS - 3 * HOUR_MS, 100, NOW_MS - HOUR_MS
    ).build()
    conditions = _conditions(payload)

    for key in ("CreatedAt", "last_sync"):
        condition = conditions[key]
        # "date_range" rounds the range start up to the next day, which would stop
        # the watermark from ever advancing within a day.
        assert condition["operator"] == "range"
        assert condition["type"] == "datetime"
        assert all(isinstance(value, str) for value in condition["values"])
        # values must be parseable, timezone-aware datetimes
        for value in condition["values"]:
            assert datetime.datetime.fromisoformat(value).tzinfo is not None


def test_no_day_granular_operator_is_used():
    payload = AlertQueryBuilder(
        NOW_MS - 3 * HOUR_MS, 100, NOW_MS - HOUR_MS
    ).build()

    operators = {
        condition.get("operator") for condition in payload["query"]["with"]["values"]
    }
    assert "date_range" not in operators


def test_start_at_index_pages_within_a_tied_cursor():
    payload = AlertQueryBuilder(NOW_MS, 100, NOW_MS).start_at_index(50).build()

    assert payload["start_at_index"] == 50


def test_parser_reads_wrapped_last_sync_value():
    """The endpoint wraps field values in {"value": ...}, including last_sync."""
    created_at = NOW_MS - 2 * HOUR_MS
    last_sync = NOW_MS - HOUR_MS
    response = build_response([build_alert_row("orca-1", created_at, last_sync)])

    alert = OrcaSecurityParser().build_alert_objects(response)[0]

    assert alert.alert_id == "orca-1"
    assert alert.last_sync == to_iso(last_sync)
    assert alert.last_sync_ms == last_sync
    assert alert.created_at_ms == created_at


def test_parser_falls_back_to_created_at_when_last_sync_absent():
    created_at = NOW_MS - 2 * HOUR_MS
    row = build_alert_row("orca-1", created_at, NOW_MS)
    del row["data"]["last_sync"]

    alert = OrcaSecurityParser().build_alert_objects(build_response([row]))[0]

    assert alert.last_sync is None
    assert alert.last_sync_ms == created_at
