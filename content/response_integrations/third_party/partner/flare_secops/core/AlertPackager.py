"""Build SOAR AlertInfo packages from Flare findings."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from soar_sdk.SiemplifyUtils import unix_now

from .constants import (
    DEVICE_PRODUCT,
    MAX_EVENTS_PER_ALERT,
    PRODUCT_NAME,
    SEVERITY_TO_ALERT_PRIORITY,
    TYPE_DISPLAY_NAME,
    VENDOR_NAME,
)


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _metadata(event: dict) -> dict:
    return _as_dict(event.get("metadata"))


def _data(event: dict) -> dict:
    return _as_dict(event.get("data"))


def _severity(event: dict) -> str:
    meta = _metadata(event)
    tenant = _as_dict(meta.get("tenant"))
    data = _data(event)
    raw = (
        tenant.get("severity")
        or data.get("severity")
        or meta.get("severity")
        or "info"
    )
    return str(raw).strip().lower() or "info"


def _source_type(event: dict) -> str:
    meta = _metadata(event)
    data = _data(event)
    return str(
        meta.get("type")
        or data.get("type")
        or event.get("event_type")
        or "unknown"
    ).strip() or "unknown"


def _uid(event: dict) -> str:
    return str(_metadata(event).get("uid") or event.get("uid") or "").strip()


def _title(event: dict) -> str:
    meta = _metadata(event)
    data = _data(event)
    for candidate in (
        meta.get("title"),
        data.get("title"),
        data.get("name"),
        meta.get("name"),
    ):
        if candidate:
            return str(candidate).strip()
    source_type = _source_type(event)
    return TYPE_DISPLAY_NAME.get(source_type, "Flare Threat Exposure Finding")


def _flare_url(event: dict) -> str:
    meta = _metadata(event)
    url = meta.get("flare_url")
    if url:
        return str(url)
    uid = _uid(event)
    if not uid:
        return ""
    return f"https://app.flare.io/firework/events/{uid}"


def _timestamp(event: dict) -> str:
    """Flare event time, preferring metadata.matched_at."""
    meta = _metadata(event)
    return str(
        meta.get("matched_at")
        or meta.get("estimated_created_at")
        or meta.get("created_at")
        or ""
    )


def _timestamp_millis(event: dict, fallback: int) -> int:
    """Convert Flare matched_at (or fallback timestamp) to Unix milliseconds."""
    raw = _timestamp(event).strip()
    if not raw:
        return fallback
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except (TypeError, ValueError):
        return fallback
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return int(parsed.astimezone(timezone.utc).timestamp() * 1000)


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, default=str)
    except Exception:
        return str(value)


def build_event_dict(event: dict, fallback_time: int) -> dict:
    """Flat SOAR event payload, timestamped from Flare metadata.matched_at."""
    meta = _metadata(event)
    uid = _uid(event)
    source_type = _source_type(event)
    severity = _severity(event)
    matched_at = _timestamp(event)
    event_time = _timestamp_millis(event, fallback_time)
    return {
        "StartTime": event_time,
        "EndTime": event_time,
        "name": _title(event),
        "device_vendor": VENDOR_NAME,
        "device_product": DEVICE_PRODUCT,
        "flare_uid": uid,
        "Severity": severity,
        "source_type": source_type,
        "source_type_display": TYPE_DISPLAY_NAME.get(
            source_type, source_type.replace("_", " ").title()
        ),
        "flare_url": _flare_url(event),
        "matched_at": matched_at,
        "estimated_created_at": matched_at,
        "tenant_id": str(meta.get("tenant_id") or ""),
        "details": _safe_json(event),
    }


def create_alerts(
    events: list,
    siemplify,
    tenant_id: int,
    logger_instance=None,
) -> list:
    """
    Group Flare findings by source type, build AlertInfo objects, batch at
    MAX_EVENTS_PER_ALERT.
    """
    # Import here so managers stay importable outside the SecOps runtime.
    from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

    log = logger_instance or siemplify.LOGGER
    if not events:
        log.info("No Flare findings to package into alerts.")
        return []

    groups: dict[str, list] = {}
    for event in events:
        source_type = _source_type(event)
        groups.setdefault(source_type, []).append(event)

    alerts = []
    current_time = unix_now()
    tenant_key = str(tenant_id or "flare")

    for source_type, group_events in groups.items():
        display_type = TYPE_DISPLAY_NAME.get(
            source_type, source_type.replace("_", " ").title()
        )
        total = len(group_events)
        num_batches = (total + MAX_EVENTS_PER_ALERT - 1) // MAX_EVENTS_PER_ALERT

        if num_batches > 1:
            log.info(
                "Splitting %s into %d alerts (%d events > %d limit).",
                display_type,
                num_batches,
                total,
                MAX_EVENTS_PER_ALERT,
            )

        for batch_num in range(num_batches):
            start_idx = batch_num * MAX_EVENTS_PER_ALERT
            end_idx = min((batch_num + 1) * MAX_EVENTS_PER_ALERT, total)
            batch = group_events[start_idx:end_idx]

            alert_id = f"{tenant_key}:{source_type}"
            alert = AlertInfo()
            alert.display_id = f"{VENDOR_NAME}:{uuid.uuid4()}"
            alert.ticket_id = alert_id
            # Stable rule_generator so SOAR closed-case remediation can find Flare alerts
            # without Google SA / Chronicle get_alerts.
            alert.rule_generator = VENDOR_NAME
            alert.device_event_class_id = alert_id
            alert.name = (
                f"{display_type}"
                if num_batches == 1
                else f"{display_type} (Part {batch_num + 1}/{num_batches})"
            )
            alert.sourceGroupIdentifier = source_type
            batch_times = [_timestamp_millis(item, current_time) for item in batch]
            alert.start_time = min(batch_times) if batch_times else current_time
            alert.end_time = max(batch_times) if batch_times else current_time
            alert.device_vendor = VENDOR_NAME
            alert.device_product = PRODUCT_NAME
            alert.environment = siemplify.context.connector_info.environment
            alert.description = (
                f"{len(batch)} Flare threat exposure finding(s) of type {source_type}."
            )
            alert.case_tags = [VENDOR_NAME, source_type, display_type]
            if num_batches > 1:
                alert.case_tags.append(f"Batch {batch_num + 1}/{num_batches}")

            highest = "info"
            for item in batch:
                severity = _severity(item)
                if SEVERITY_TO_ALERT_PRIORITY.get(severity, 0) >= SEVERITY_TO_ALERT_PRIORITY.get(
                    highest, 0
                ):
                    highest = severity
                alert.events.append(
                    build_event_dict(item, current_time)
                )

            alert.Severity = highest
            alert.priority = SEVERITY_TO_ALERT_PRIORITY.get(highest, 40)
            alert.extensions = {
                "SourceType": source_type,
                "SourceTypeDisplay": display_type,
                "FindingCount": len(batch),
                "TotalFindingCount": total,
                "TenantId": tenant_key,
                "CaseId": alert_id,
            }
            if num_batches > 1:
                alert.extensions["BatchNumber"] = batch_num + 1
                alert.extensions["TotalBatches"] = num_batches

            alerts.append(alert)

    log.info("---- Total Alerts Generated: %d ----", len(alerts))
    return alerts
