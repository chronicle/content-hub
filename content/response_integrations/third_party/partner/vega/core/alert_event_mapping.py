"""Map one Vega alert event onto a SOAR event."""

from __future__ import annotations

from typing import Any

from .constants import DEVICE_PRODUCT, ENTITY_TYPE_ALERT, VENDOR_NAME
from .mapping import (
    _MAX_DETAILS_CHARS,
    _MAX_EXTRA_FIELDS,
    _apply_entity_aliases,
    _apply_event_times,
    _apply_label_fields,
    _flatten_entities,
    _has_mapped_value,
    _is_skipped_payload_key,
    _set_mapped,
    _soar_key,
    _soar_value,
    normalize_alert_event,
    record_id,
    record_severity,
    soar_meta,
)

def _is_flat_dict(value: dict) -> bool:
    return all(not isinstance(item, (dict, list)) for item in value.values())


def _iter_dynamic_fields(payload: dict):
    """Yield API keys/values from getAlertsEvents, flattening one-level dicts."""
    for key, value in payload.items():
        if _is_skipped_payload_key(key):
            continue
        if not _has_mapped_value(value):
            continue
        if isinstance(value, dict) and _is_flat_dict(value):
            for nested_key, nested_value in value.items():
                if _is_skipped_payload_key(nested_key):
                    continue
                if not _has_mapped_value(nested_value):
                    continue
                yield nested_key, nested_value
            continue
        yield key, value


def build_vega_alert_event_dict(
    parent: dict,
    vega_event: Any,
    start_time: int,
    end_time: int,
    index: int,
) -> dict:
    """Map one Vega getAlertsEvents result onto a SOAR event for a Vega Alert case.

    Child events must use a unique product_log_id and only string field values.
    Shared IDs or nested/Splunk-style keys cause SecOps to drop them from the case.
    Fields are taken from the API payload as-is; empty values are omitted.
    """
    identifier = record_id(parent, ENTITY_TYPE_ALERT)
    payload = normalize_alert_event(vega_event)
    event_key = f"{identifier}:event:{index}"
    name = str(
        payload.get("name")
        or payload.get("summary")
        or payload.get("message")
        or payload.get("eventName")
        or payload.get("event_name")
        or payload.get("sourcetype")
        or f"Vega Alert Event {index + 1}"
    ).strip()
    meta = soar_meta(parent)
    incident_id = str(meta.get("incident_id") or parent.get("vega_incident_id") or "").strip()
    event = {
        "StartTime": start_time,
        "EndTime": end_time,
        "name": name,
        "device_vendor": VENDOR_NAME,
        "device_product": DEVICE_PRODUCT,
        "product": DEVICE_PRODUCT,
        "event_type": "Alert Event",
        "product_log_id": event_key,
        "vega_id": identifier,
        "event_class_id": event_key,
        "DeviceEventClassID": event_key,
        "Severity": record_severity(parent),
        "vega_entity_type": "Alert Event",
    }
    _set_mapped(event, "vega_alert_id", parent.get("vegaAlertId"))
    _set_mapped(event, "vega_incident_id", incident_id)
    extra = 0
    for key, value in _iter_dynamic_fields(payload):
        if extra >= _MAX_EXTRA_FIELDS:
            break
        safe_key = _soar_key(key)
        if not safe_key or safe_key in event or _is_skipped_payload_key(safe_key):
            continue
        event[safe_key] = _soar_value(value)
        extra += 1
    # Related-alert cases are mostly these child events. Copy the parent
    # Vega Alert labels so Default/Events is not an empty `labels` list.
    _apply_label_fields(event, parent, copy_incident_names=True)
    details_payload = {key: value for key, value in payload.items() if _has_mapped_value(value)}
    if details_payload:
        event["details"] = _soar_value(details_payload, limit=_MAX_DETAILS_CHARS)
    event.update(_flatten_entities(payload))
    _apply_entity_aliases(event, payload)
    _apply_event_times(event, start_time, end_time)
    return event

