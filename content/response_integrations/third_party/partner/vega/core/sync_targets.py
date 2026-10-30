"""Read Vega ids from a closed SOAR case payload."""

from __future__ import annotations

import json

from .constants import ENTITY_TYPE_ALERT, ENTITY_TYPE_INCIDENT, VENDOR_NAME

SYNC_MODE_INCIDENT = "incident"
SYNC_MODE_ALERTS = "alerts"

_VEGA_ID_KEYS = (
    "vega_id",
    "vegaId",
    "product_log_id",
    "productLogId",
    "event_class_id",
    "eventClassId",
    "DeviceEventClassID",
    "DeviceEventClassId",
    "incidentId",
    "ticketId",
    "ticket_id",
    "vegaAlertId",
    "vega_alert_id",
    "vegaUniqueIncidentId",
    "vega_unique_incident_id",
)
_ENTITY_TYPE_KEYS = (
    "vega_entity_type",
    "vegaEntityType",
    "event_type",
    "eventType",
    "vega_soar_alert_type",
    "vegaSoarAlertType",
)


def _normalize_vega_identifier(value: str) -> str:
    """Strip ``Vega:`` tickets and prefer a UUID prefix over a suffix."""
    from .mapping import is_graphql_alert_id

    text = str(value or "").strip()
    if not text:
        return ""
    prefix = f"{VENDOR_NAME}:"
    if text.startswith(prefix) or text.lower().startswith(prefix.lower()):
        text = text.split(":", 1)[1].strip()
    if is_graphql_alert_id(text):
        return text
    head = text.split(":", 1)[0].strip()
    if is_graphql_alert_id(head):
        return head
    return text


def _event_vega_id(event: dict) -> str:
    """Own Vega ID for this event. GraphQL UUID wins over VINC-/vegaAlertId."""
    if not isinstance(event, dict):
        return ""
    from .mapping import is_graphql_alert_id

    candidates: list[str] = []
    for key in _VEGA_ID_KEYS:
        raw = str(event.get(key) or "").strip()
        if not raw:
            continue
        value = _normalize_vega_identifier(raw)
        if value and value not in candidates:
            candidates.append(value)
    usable = [item for item in candidates if not _is_child_event_id(item)]
    pool = usable or candidates
    for item in pool:
        if is_graphql_alert_id(item):
            return item
    return pool[0] if pool else ""


def _event_entity_type(event: dict) -> str:
    """Incident, Alert, or empty when SOAR omitted the type fields."""
    if not isinstance(event, dict):
        return ""
    for key in _ENTITY_TYPE_KEYS:
        raw = str(event.get(key) or "").strip().lower()
        if raw in ("incident", "vega incident"):
            return ENTITY_TYPE_INCIDENT
        if raw in ("alert", "vega alert", "alert event"):
            return ENTITY_TYPE_ALERT
    return ""


def _is_child_event_id(identifier: str) -> bool:
    return ":event:" in identifier


def _is_alert_event(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    for key in _ENTITY_TYPE_KEYS:
        if str(payload.get(key) or "").strip().lower() == "alert event":
            return True
    return False


def _as_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip().startswith("{"):
        try:
            parsed = json.loads(value)
        except Exception:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _fields_from_event_card(card: dict) -> dict:
    payload: dict = {}
    for group in card.get("fields") or []:
        if not isinstance(group, dict):
            continue
        for item in group.get("items") or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("originalName") or item.get("name") or "").strip()
            if key:
                payload[key] = item.get("value")
    return payload


def _flatten_event(event: dict) -> dict:
    payload = dict(event) if isinstance(event, dict) else {}
    extra = _as_dict(
        payload.get("additional_properties")
        or payload.get("additionalProperties")
        or payload.get("AdditionalProperties")
    )
    field_values = _fields_from_event_card(payload)
    merged = dict(extra)
    merged.update(field_values)
    merged.update(payload)
    return merged


def _iter_case_events(case_payload: dict) -> list[dict]:
    """Events from a case dict (SDK ticket payload or GetCaseFullDetails)."""
    if not isinstance(case_payload, dict):
        return []
    direct = (
        case_payload.get("events") or case_payload.get("security_events") or case_payload.get("securityEvents") or []
    )
    events: list[dict] = [item for item in direct if isinstance(item, dict)]
    alerts = (
        case_payload.get("cyber_alerts")
        or case_payload.get("cyberAlerts")
        or case_payload.get("alerts")
        or case_payload.get("alertCards")
        or case_payload.get("alert_cards")
        or []
    )
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        nested = (
            alert.get("security_events")
            or alert.get("securityEvents")
            or alert.get("events")
            or alert.get("involvedRelations")
            or alert.get("involved_relations")
            or alert.get("securityEventCards")
            or alert.get("security_event_cards")
            or []
        )
        events.extend(item for item in nested if isinstance(item, dict))
        extra = _as_dict(alert.get("additional_properties") or alert.get("additionalProperties"))
        stub = dict(extra)
        for key in (
            "ticketId",
            "ticket_id",
            "deviceEventClassId",
            "device_event_class_id",
            "DeviceEventClassId",
            "vega_entity_type",
            "vegaEntityType",
            "event_type",
            "eventType",
        ):
            value = alert.get(key)
            if value not in (None, "") and key not in stub:
                stub[key] = value
        if stub:
            events.append(stub)
    return events


def _walk_vega_targets(payload, entity_hint: str = "") -> list[tuple[str, str]]:
    """Find Vega IDs anywhere in a GetCaseFullDetails payload."""
    found: list[tuple[str, str]] = []
    if isinstance(payload, list):
        for item in payload:
            found.extend(_walk_vega_targets(item, entity_hint))
        return found
    if not isinstance(payload, dict):
        return found
    hinted = entity_hint
    typed = _event_entity_type(payload)
    if typed == ENTITY_TYPE_INCIDENT:
        hinted = ENTITY_TYPE_INCIDENT
    elif typed == ENTITY_TYPE_ALERT:
        hinted = ENTITY_TYPE_ALERT
    identifier = _event_vega_id(payload)
    if identifier and not _is_alert_event(payload):
        found.append((identifier, hinted))
    for value in payload.values():
        if isinstance(value, (dict, list)):
            found.extend(_walk_vega_targets(value, hinted))
    return found


def extract_sync_targets(case_payload: dict) -> dict:
    """Classify a closed case as incident-only or alerts-only.

    Incident case → resolve the Vega incident only.
    Related-alert case or unrelated alert case → resolve those Vega alerts
    only. ``vega_incident_id`` on related alerts is not a close target.
    """
    incident_ids: list[str] = []
    alert_ids: list[str] = []
    seen_incidents: set[str] = set()
    seen_alerts: set[str] = set()
    from .Remediator import _is_incident_case_title

    title_is_incident = _is_incident_case_title(case_payload)
    for event in _iter_case_events(case_payload):
        payload = _flatten_event(event)
        identifier = _event_vega_id(payload)
        if _is_alert_event(payload) or _is_child_event_id(identifier):
            continue
        entity_type = _event_entity_type(payload)
        if entity_type == ENTITY_TYPE_INCIDENT or (not entity_type and title_is_incident):
            if identifier and identifier not in seen_incidents:
                seen_incidents.add(identifier)
                incident_ids.append(identifier)
            continue
        if identifier and identifier not in seen_alerts:
            seen_alerts.add(identifier)
            alert_ids.append(identifier)
    if not incident_ids and not alert_ids:
        for identifier, entity_type in _walk_vega_targets(case_payload):
            if _is_child_event_id(identifier):
                continue
            if entity_type == ENTITY_TYPE_INCIDENT or (not entity_type and title_is_incident):
                if identifier not in seen_incidents:
                    seen_incidents.add(identifier)
                    incident_ids.append(identifier)
            elif identifier not in seen_alerts:
                seen_alerts.add(identifier)
                alert_ids.append(identifier)
    if incident_ids:
        return {
            "mode": SYNC_MODE_INCIDENT,
            "incident_ids": incident_ids,
            "alert_ids": [],
        }
    return {
        "mode": SYNC_MODE_ALERTS,
        "incident_ids": [],
        "alert_ids": alert_ids,
    }
