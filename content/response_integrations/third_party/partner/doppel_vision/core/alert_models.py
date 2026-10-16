from __future__ import annotations

from typing import Any


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return []


def normalize_alert(raw_alert: Any) -> dict[str, Any] | None:
    """Normalize a v1 or v2 alert payload into a common internal model.

    Actions still return the raw API JSON to playbooks. This helper is used
    internally so v1/v2 field aliases stay consistent.
    """
    if not isinstance(raw_alert, dict):
        return None

    return {
        "id": raw_alert.get("id") or None,
        "entity": raw_alert.get("entity"),
        "entity_content": raw_alert.get("entity_content") if isinstance(raw_alert.get("entity_content"), dict) else {},
        "severity": raw_alert.get("severity"),
        "tags": _as_list(raw_alert.get("tags")),
        "audit_logs": _as_list(raw_alert.get("audit_logs")),
        "queue_state": raw_alert.get("queue_state"),
        "entity_state": raw_alert.get("entity_state"),
        "product": raw_alert.get("product"),
        "platform": raw_alert.get("platform"),
        "source": raw_alert.get("source"),
        "created_at": raw_alert.get("created_at"),
        "last_activity_timestamp": raw_alert.get("last_activity_timestamp") or raw_alert.get("last_activity"),
        "notes": raw_alert.get("notes") if raw_alert.get("notes") is not None else raw_alert.get("note"),
        "uploaded_by": raw_alert.get("uploaded_by"),
        "brand": raw_alert.get("brand"),
        "assignee": raw_alert.get("assignee"),
        "alert_summary": raw_alert.get("alert_summary"),
        "doppel_link": raw_alert.get("doppel_link"),
        "score": raw_alert.get("score"),
        "screenshot_url": raw_alert.get("screenshot_url"),
    }


def normalize_alert_list(raw_alerts: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_alerts, list):
        return []
    return [alert for alert in (normalize_alert(item) for item in raw_alerts) if alert]
