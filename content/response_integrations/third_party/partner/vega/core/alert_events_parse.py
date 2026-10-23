"""Parse getAlertsEvents rows into per-alert buckets."""

from __future__ import annotations

import json
from typing import Any

def _unwrap_json(value: Any, *, depth: int = 3) -> Any:
    """Decode JSON strings, including double-encoded payloads."""
    current = value
    for _ in range(depth):
        if not isinstance(current, str):
            return current
        text = current.strip()
        if not text:
            return current
        if text[0] not in '{["':
            return current
        try:
            current = json.loads(text)
        except json.JSONDecodeError:
            return current
    return current


def _rows_to_event_dicts(fields: list, rows: list) -> list[dict]:
    """Convert Splunk-style `{fields, rows}` tables into event dicts."""
    colnames: list[str] = []
    for field in fields:
        if isinstance(field, dict):
            colnames.append(str(field.get("name") or field.get("field") or "").strip())
        else:
            colnames.append(str(field).strip())
    if not colnames:
        return []
    parsed: list[dict] = []
    for row in rows:
        if not isinstance(row, list):
            continue
        event = {colnames[index]: row[index] for index in range(min(len(colnames), len(row))) if colnames[index]}
        if event:
            parsed.append(event)
    return parsed


def parse_alert_events_results(results: Any) -> list[dict]:
    """Normalize getAlertsEvents `results` (list, dict, or JSON string) into event dicts."""
    if results is None or results == "":
        return []
    results = _unwrap_json(results)
    if isinstance(results, dict):
        fields = results.get("fields")
        rows = results.get("rows")
        if isinstance(fields, list) and isinstance(rows, list) and rows and not isinstance(rows[0], dict):
            tabular = _rows_to_event_dicts(fields, rows)
            if tabular:
                return tabular
        for key in ("results", "events", "items", "data", "rows"):
            nested = results.get(key)
            if isinstance(nested, list):
                results = nested
                break
        else:
            results = [results]
    if not isinstance(results, list):
        return []
    parsed: list[dict] = []
    for item in results:
        item = _unwrap_json(item)
        if isinstance(item, dict):
            parsed.append(item)
    return parsed


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _graphql_alert_id(value: str) -> bool:
    from .mapping import is_graphql_alert_id

    return is_graphql_alert_id(value)


def _same_alert_id(left: str, right: str) -> bool:
    if left == right:
        return True
    if _graphql_alert_id(left) and _graphql_alert_id(right):
        return left.casefold() == right.casefold()
    return False


def _event_owner_id(event: dict) -> str:
    """Alert id stamped on a getAlertsEvents row, when the row has one."""
    for key in ("alertId", "alert_id", "vegaAlertId"):
        value = str(event.get(key) or "").strip()
        if value:
            return value
    return ""


def events_for_alert_bucket(results: Any, alert_id: str) -> tuple[list[dict], int]:
    """Keep rows for `alert_id` and count rows that belong to some other alert.

    Rows with no alert id stay in the parent `alerts[].alertId` bucket. Rows
    tagged with a different alert id are dropped so events are not copied
    onto the wrong alert.
    """
    alert_id = str(alert_id or "").strip()
    kept: list[dict] = []
    dropped = 0
    for event in parse_alert_events_results(results):
        owner = _event_owner_id(event)
        if owner and not _same_alert_id(owner, alert_id):
            dropped += 1
            continue
        kept.append(event)
    return kept, dropped


