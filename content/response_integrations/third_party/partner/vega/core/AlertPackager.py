"""Build SOAR AlertInfo packages from Vega signals (incident-linked alerts)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

from .alert_event_mapping import build_vega_alert_event_dict
from .constants import (
    DEVICE_PRODUCT,
    ENTITY_TYPE_ALERT,
    MAX_EVENTS_PER_ALERT_DEFAULT,
    SYNC_ALERTS_TAG,
    VENDOR_NAME,
)
from .mapping import (
    alert_priority,
    normalize_alert_event,
    record_id,
    record_name,
    record_severity,
    signal_rule_generator,
    signal_ticket_id,
    soar_meta,
)
from .utils import parse_iso_timestamp, safe_log

# Reject epoch-0 / 1970 timestamps and values that are not real event times.
_MIN_VALID_EVENT_MS = 946684800000  # 2000-01-01
_MAX_VALID_EVENT_MS = 4102444800000  # 2100-01-01


def _coerce_unix_ms(raw: Any) -> int | None:
    if raw in (None, "", 0, "0"):
        return None
    value = None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        value = float(raw)
    else:
        text = str(raw).strip()
        if not text or text in {"0", "0.0"}:
            return None
        if text.isdigit() or (text.replace(".", "", 1).isdigit() and text.count(".") < 2):
            value = float(text)
        else:
            parsed = parse_iso_timestamp(text)
            if parsed is None:
                return None
            millis = int(parsed.timestamp() * 1000)
            if millis < _MIN_VALID_EVENT_MS or millis > _MAX_VALID_EVENT_MS:
                return None
            return millis
    if value is None or value <= 0:
        return None
    if value < 1e12:
        value *= 1000
    millis = int(value)
    if millis < _MIN_VALID_EVENT_MS or millis > _MAX_VALID_EVENT_MS:
        return None
    return millis


def _field_ms(record: SingleJson, *keys: str) -> int | None:
    if not isinstance(record, dict):
        return None
    for key in keys:
        coerced = _coerce_unix_ms(record.get(key))
        if coerced is not None:
            return coerced
    return None


def record_start_end(record: SingleJson, fallback: int) -> tuple[int, int]:
    """Incident and alert window: start is createdAt, end is last update."""
    start = _field_ms(record, "createdAt")
    end = _field_ms(record, "lastUpdated", "updatedAt")
    if start is None:
        start = fallback
    if end is None:
        end = start
    return start, end


def _time_values(payload: SingleJson) -> list[int]:
    found: list[int] = []
    if not isinstance(payload, dict):
        return found
    for key, value in payload.items():
        if isinstance(value, dict):
            found.extend(_time_values(value))
            continue
        if "time" not in str(key).lower():
            continue
        coerced = _coerce_unix_ms(value)
        if coerced is not None:
            found.append(coerced)
    return found


def event_start_end(payload: SingleJson, parent_start: int, parent_end: int) -> tuple[int, int]:
    times = _time_values(payload if isinstance(payload, dict) else {})
    if not times:
        return parent_start, parent_end
    return min(times), max(times)


def _attach_vega_alert_events(
    alert: Any,
    record: SingleJson,
    parent_start: int,
    parent_end: int,
    max_events: int,
    logger_instance: Any = None,
) -> None:
    """Attach only Vega alert-events as SecOps events (no parent alert event)."""
    identifier = record_id(record, ENTITY_TYPE_ALERT)
    child_events = list(record.get("alert_events") or [])
    cap = max(0, int(max_events))
    if cap == 0:
        return
    if len(child_events) > cap:
        safe_log(
            logger_instance,
            "info",
            "Vega alert %s has %s alert-events; attaching the first %s (Max Events in Alert).",
            identifier,
            len(child_events),
            cap,
        )
        child_events = child_events[:cap]
    for index, vega_event in enumerate(child_events):
        payload = vega_event if isinstance(vega_event, dict) else {}
        normalized = normalize_alert_event(payload) if payload else {}
        child_start, child_end = event_start_end(normalized, parent_start, parent_end)
        child = build_vega_alert_event_dict(record, vega_event, child_start, child_end, index)
        alert.events.append(child)


def create_alerts(
    records: list[tuple[str, SingleJson]],
    siemplify: Any,
    logger_instance: Any = None,
    max_events_in_alert: int = MAX_EVENTS_PER_ALERT_DEFAULT,
) -> list[Any]:
    """Turn pipeline signal records into SOAR AlertInfo packages.

    One Vega incident → one SecOps case via shared ``Vega:incident:<id>``.
    No SecOps event for the Vega alert itself; only Vega alert-events become
    SecOps events. Case name = rule_generator ``{vegaUniqueIncidentId} - {name}``.
    """
    from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
    from soar_sdk.SiemplifyUtils import unix_now

    if not records:
        return []
    current_time = unix_now()
    environment = ""
    try:
        environment = siemplify.context.connector_info.environment
    except Exception:
        environment = ""
    packages = []
    max_events = max(0, int(max_events_in_alert))
    for entity_type, record in records:
        if entity_type != ENTITY_TYPE_ALERT:
            continue
        identifier = record_id(record, entity_type)
        if not identifier:
            continue
        meta = soar_meta(record)
        start_time, end_time = record_start_end(record, current_time)
        severity = record_severity(record)
        incident_id = str(meta.get("incident_id") or "").strip()
        if not incident_id:
            continue
        ticket_id = signal_ticket_id(incident_id, identifier)
        grouping_id = f"{VENDOR_NAME}:incident:{incident_id}"
        rank = int(meta.get("signal_rank") or 1)
        signal_name = record_name(record)
        case_title = str(meta.get("case_title") or "").strip()
        if not case_title:
            display = str(meta.get("incident_display_id") or "").strip()
            incident_name = str(meta.get("incident_name") or "").strip()
            case_title = f"{display} - {incident_name}".strip(" -") if display or incident_name else signal_name
        incident_summary = str(
            meta.get("incident_summary")
            or record.get("incidentSummary")
            or ""
        ).strip()
        case_tags = [SYNC_ALERTS_TAG]
        for name in meta.get("case_tags") or []:
            text = str(name or "").strip()
            if text and text not in case_tags:
                case_tags.append(text)
        alert = AlertInfo()
        alert.display_id = ticket_id
        alert.ticket_id = ticket_id
        alert.rule_generator = case_title
        alert.device_event_class_id = ticket_id
        alert.name = signal_rule_generator(rank, signal_name)
        alert.device_vendor = VENDOR_NAME
        alert.device_product = DEVICE_PRODUCT
        alert.source_grouping_identifier = grouping_id
        alert.environment = environment
        # Case Description is set by SyncAlerts; alert description is a fallback.
        alert.description = incident_summary or str(
            record.get("description") or record.get("detectionDescription") or signal_name
        )
        alert.case_tags = case_tags
        alert.start_time = start_time
        alert.end_time = end_time
        alert.Severity = severity
        alert.priority = alert_priority(severity)
        alert.extensions = {
            "vega_entity_type": entity_type,
            "vega_id": identifier,
            "vega_incident_id": incident_id,
            "vega_signal_rank": rank,
            "vega_total_signals": meta.get("total_signals"),
            "vega_signals_in_case": meta.get("signals_in_case"),
            "vega_incident_link": meta.get("incident_link") or "",
            "SourceGroupingIdentifier": grouping_id,
        }
        _attach_vega_alert_events(
            alert,
            record,
            start_time,
            end_time,
            max_events,
            logger_instance,
        )
        packages.append(alert)
    return packages
