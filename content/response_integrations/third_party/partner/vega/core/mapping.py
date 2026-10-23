"""Map Vega alert/incident records to SOAR event dictionaries."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


import json
import re
from .constants import (
    DEVICE_PRODUCT,
    ENTITY_TYPE_ALERT,
    ENTITY_TYPE_INCIDENT,
    SEVERITY_TO_ALERT_PRIORITY,
    SOAR_ALERT_TYPE_ALERT,
    SOAR_ALERT_TYPE_INCIDENT,
    SOAR_META_KEY,
    VENDOR_NAME,
)

_SAFE_KEY_RE = re.compile(r"[^A-Za-z0-9_]")
_GRAPHQL_ID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_MAX_EVENT_FIELD_CHARS = 10000
_MAX_DETAILS_CHARS = 100000
_MAX_EXTRA_FIELDS = 80
_SKIP_PAYLOAD_KEYS = {
    "fields",
    "_raw",
    "raw",
    "details",
    "StartTime",
    "EndTime",
    "start_time",
    "end_time",
    "name",
    "device_vendor",
    "device_product",
    "product",
    "event_type",
    "product_log_id",
    "vega_id",
    "event_class_id",
    "DeviceEventClassID",
    "Severity",
    "time",
    "Time",
    "_time",
    "timestamp",
    "eventTime",
    "event_time",
    "datetime",
    "date",
    "labels",
    "vega_label_names",
    "vega_labels",
    "vega_incident_label_names",
}
# Vega/Splunk payloads use mixed-case time keys. SecOps ontology maps StartTime
# from the event; extra time fields overwrite it or show as 1970/invalid.
_SKIP_TIME_NORMALIZED = {
    "starttime",
    "endtime",
    "time",
    "timestamp",
    "eventtime",
    "datetime",
    "date",
    "occurredat",
    "origintime",
    "indextime",
}
RESET_USER_PASSWORD_ACTION_KEY = "reset_user_password"

_ENTITY_ALIASES = {
    "src_ip": "ip",
    "srcip": "ip",
    "source_ip": "ip",
    "sourceip": "ip",
    "dest_ip": "ip",
    "dst_ip": "ip",
    "dstip": "ip",
    "destination_ip": "ip",
    "client_ip": "ip",
    "ip_address": "ip",
    "src_host": "hostname",
    "dest_host": "hostname",
    "computer": "hostname",
    "computer_name": "hostname",
    "src_user": "user",
    "dest_user": "user",
    "user_name": "user",
    "username": "user",
    "account": "user",
    "filehash": "hash",
    "file_hash": "hash",
    "md5": "hash",
    "sha1": "hash",
    "sha256": "hash",
    "request_url": "url",
    "http_url": "url",
    "fqdn": "hostname",
    "domain_name": "domain",
}


def _as_dict(value: Any) -> SingleJson:
    return value if isinstance(value, dict) else {}


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, default=str)
    except Exception:
        return str(value)


def soar_meta(record: SingleJson) -> SingleJson:
    """Return the private SOAR metadata bag stored on a Vega record."""
    meta = record.get(SOAR_META_KEY) if isinstance(record, dict) else None
    return dict(meta) if isinstance(meta, dict) else {}


def set_soar_meta(record: SingleJson, **fields: Any) -> SingleJson:
    """Return a copy of the record with updated private SOAR metadata fields."""
    updated = dict(record or {})
    meta = soar_meta(updated)
    meta.update({key: value for key, value in fields.items() if value is not None})
    updated[SOAR_META_KEY] = meta
    return updated


def record_id(record: SingleJson, entity_type: str) -> str:
    """Return the canonical Vega id for an alert or incident record."""
    if entity_type == ENTITY_TYPE_INCIDENT:
        return str(record.get("id") or record.get("incidentId") or "").strip()
    return str(record.get("id") or record.get("vegaAlertId") or record.get("alertId") or "").strip()


def record_alert_ids(record: SingleJson) -> list[str]:
    """IDs to try with getAlertsEvents: UUID first, then human vegaAlertId."""
    ids: list[str] = []
    for key in ("id", "vegaAlertId", "alertId"):
        value = str(record.get(key) or "").strip()
        if value and value not in ids:
            ids.append(value)
    return ids


def is_graphql_alert_id(value: str) -> bool:
    """True for UUID alertIds safe in getAlerts(alertIds: [ID!])."""
    return bool(_GRAPHQL_ID_RE.match(str(value or "").strip()))


def record_display_id(record: SingleJson, entity_type: str) -> str:
    """Human-facing Vega ID used in the SOAR alert/case title.

    Vega Alert names use vegaAlertId only (never the UUID id/alertId).
    """
    if entity_type == ENTITY_TYPE_INCIDENT:
        return str(record.get("vegaUniqueIncidentId") or record.get("incidentId") or "").strip()
    return str(record.get("vegaAlertId") or "").strip()


def record_name(record: SingleJson) -> str:
    """Return the display name from a Vega alert or incident record."""
    return str(record.get("name") or record.get("incidentName") or "Vega record").strip()


def case_display_name(record: SingleJson, entity_type: str) -> str:
    """Human-readable SOAR alert/case title: Vega {entity} - {display_id} - {name}.

    Alert Type in SOAR search is rule_generator. For incident-case members the
    packager sets Rule Generator to the incident case title and Name to this
    per-record title (Vega Incident vs Vega Alert).
    """
    display_id = record_display_id(record, entity_type)
    name = record_name(record)
    if display_id:
        return f"Vega {entity_type} - {display_id} - {name} FEEDBACK TEST 13"
    return f"Vega {entity_type} - {name} FEEDBACK TEST 13"


# Marks the related-alert case so close-sync does not treat it as the incident.
RELATED_ALERTS_TITLE_MARK = "(related alerts)"


def incident_case_title(record: SingleJson, related: bool = False, batch: int | None = None) -> str:
    """SOAR case title for the incident case or one related-alert chunk.

    Related alerts use ``(cluster N)`` in chunks of up to 90. ``N`` advances per
    incident in the connector checkpoint so cluster numbers are not reused.
    """
    title = case_display_name(record, ENTITY_TYPE_INCIDENT)
    if batch:
        return f"{title} (cluster {int(batch)})"
    if related:
        return f"{title} {RELATED_ALERTS_TITLE_MARK}"
    return title


def incident_grouping_id(incident_id: str, related: bool = False, batch: int | None = None) -> str:
    """SOAR source grouping key.

    The incident case is ``Vega:incident:<id>``. Related alerts use one
    grouping key per cluster chunk: ``Vega:incident:<id>:related:cluster:<N>``.
    Legacy ``related=True`` without ``batch`` keeps ``...:related``.
    """
    base = f"{VENDOR_NAME}:incident:{incident_id}"
    if batch:
        return f"{base}:related:cluster:{int(batch)}"
    if related:
        return f"{base}:related"
    return base


def alert_grouping_id(alert_id: str) -> str:
    """Return the SOAR source grouping id for a standalone Vega alert."""
    return f"{VENDOR_NAME}:alert:{alert_id}"


def _label_items(value: Any) -> list:
    labels = value
    if isinstance(labels, str) and labels.strip():
        parsed = _try_parse_json(labels)
        labels = parsed if parsed is not labels else [labels]
    if isinstance(labels, dict):
        labels = labels.get("items") or labels.get("nodes") or labels.get("labels") or list(labels.values())
    if not isinstance(labels, list):
        return []
    return labels


def _display_labels(value: Any) -> list[SingleJson]:
    """Keep only Vega label name and color on SOAR events."""
    displayed: list[SingleJson] = []
    for item in _label_items(value):
        if isinstance(item, str):
            name = item.strip()
            if name:
                displayed.append({"name": name})
            continue
        if not isinstance(item, dict):
            continue
        name = str(
            item.get("name") or item.get("label") or item.get("labelName") or item.get("displayName") or ""
        ).strip()
        color = str(item.get("color") or "").strip()
        if not name and not color:
            continue
        entry: dict[str, str] = {}
        if name:
            entry["name"] = name
        if color:
            entry["color"] = color
        displayed.append(entry)
    return displayed


def record_label_tags(record: SingleJson) -> list[str]:
    """SOAR case tags from Vega incident or alert `labels` names.

    SecOps creates a tag on first use when AlertInfo.case_tags is set, so
    names do not need to exist in Settings first. Names shorter than 2
    characters are skipped (SOAR rejects them).
    """
    tags: list[str] = []
    seen: set[str] = set()
    labels = record.get("labels") if isinstance(record, dict) else None
    for item in _label_items(labels):
        name = ""
        if isinstance(item, str):
            name = item.strip()
        elif isinstance(item, dict):
            name = str(
                item.get("name") or item.get("label") or item.get("labelName") or item.get("displayName") or ""
            ).strip()
        if len(name) < 2:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        tags.append(name)
    return tags


def collect_label_tags(*records: SingleJson) -> list[str]:
    """Unique case tags from an incident and every related alert in the case."""
    tags: list[str] = []
    seen: set[str] = set()
    for record in records:
        for name in record_label_tags(record or {}):
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            tags.append(name)
    return tags


_LABEL_TAG_KEYS = (
    "labels",
    "vega_label_names",
    "vega_labels",
    "vega_incident_label_names",
)


def flatten_event_for_tags(event: Any) -> SingleJson:
    """SOAR events store Vega fields on the object, in additional_properties, or in details JSON."""
    payload: SingleJson = {}
    if isinstance(event, dict):
        payload.update(event)
    elif event is not None:
        extra = getattr(event, "additional_properties", None)
        if isinstance(extra, dict):
            payload.update(extra)
        raw = getattr(event, "__dict__", None)
        if isinstance(raw, dict):
            for key, value in raw.items():
                if str(key).startswith("_"):
                    continue
                payload.setdefault(key, value)
        fields = getattr(event, "fields", None)
        if isinstance(fields, list):
            payload.setdefault("fields", fields)
    nested = payload.get("additional_properties") or payload.get("AdditionalProperties")
    merged: SingleJson = {}
    if isinstance(nested, dict):
        merged.update(nested)
    for key, value in payload.items():
        if key in ("additional_properties", "AdditionalProperties"):
            continue
        merged[key] = value
    fields = merged.get("fields")
    if isinstance(fields, list):
        for item in fields:
            if not isinstance(item, dict):
                continue
            key = item.get("key") or item.get("name") or item.get("field")
            if key and "value" in item:
                merged.setdefault(str(key), item.get("value"))
    details = _try_parse_json(merged.get("details"))
    if isinstance(details, dict):
        for key in _LABEL_TAG_KEYS:
            if key in details and merged.get(key) in (None, "", [], {}):
                merged[key] = details.get(key)
    return merged


def tags_from_event_fields(event: Any) -> list[str]:
    """Vega label names stored on a SOAR event (JSON labels or comma-separated names)."""
    event = flatten_event_for_tags(event)
    blobs: list = []
    for key in _LABEL_TAG_KEYS:
        value = event.get(key)
        if value in (None, "", [], {}):
            continue
        if isinstance(value, str):
            parsed = _try_parse_json(value)
            blobs.append(parsed if parsed is not value else [part.strip() for part in value.split(",") if part.strip()])
        else:
            blobs.append(value)
    return collect_label_tags(*[{"labels": blob} for blob in blobs])


def pending_case_tags(names: list[str], existing: list[str] | set[str] | None = None) -> list[str]:
    """Drop blank, short, and already-assigned tag names (case-insensitive)."""
    seen = {str(name).strip().casefold() for name in (existing or []) if str(name).strip()}
    pending: list[str] = []
    for name in names or []:
        text = str(name).strip()
        key = text.casefold()
        if len(text) < 2 or key in seen:
            continue
        seen.add(key)
        pending.append(text)
    return pending


def tags_from_events(events: list[Any]) -> list[str]:
    """Extract unique Vega label tag names from a list of SOAR events."""
    return collect_label_tags(*[{"labels": tags_from_event_fields(event)} for event in (events or [])])


def incident_alert_summary(stub: SingleJson) -> SingleJson:
    """alertId, name, and createdAt from a getIncidents nested alert."""
    stub = stub if isinstance(stub, dict) else {}
    alert_id = str(stub.get("alertId") or stub.get("id") or "").strip()
    if not alert_id:
        return {}
    summary = {"alertId": alert_id}
    name = str(stub.get("name") or "").strip()
    created_at = str(stub.get("createdAt") or "").strip()
    if name:
        summary["name"] = name
    if created_at:
        summary["createdAt"] = created_at
    return summary


def incident_alert_stubs(incident: SingleJson) -> list[SingleJson]:
    """Return nested alert stub dicts from a getIncidents record."""
    raw = incident.get("alerts") if isinstance(incident, dict) else None
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    stubs: list[SingleJson] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            stubs.append({"alertId": item.strip(), "id": item.strip()})
        elif isinstance(item, dict):
            stubs.append(item)
    return stubs


def incident_alert_ids(incident: SingleJson) -> list[str]:
    """Unique alert IDs from getIncidents `alerts { alertId name createdAt }`."""
    ids: list[str] = []
    seen: set[str] = set()
    for stub in incident_alert_stubs(incident):
        for key in record_alert_ids(stub):
            if key not in seen:
                seen.add(key)
                ids.append(key)
    return ids


def stub_to_alert(stub: SingleJson) -> SingleJson:
    """Expand a nested incident alert stub into a minimal alert record."""
    stub = stub if isinstance(stub, dict) else {}
    alert_id = str(stub.get("alertId") or stub.get("id") or stub.get("vegaAlertId") or "").strip()
    return {
        "id": alert_id,
        "alertId": alert_id,
        "vegaAlertId": str(stub.get("vegaAlertId") or "").strip(),
        "name": stub.get("name") or "Vega alert",
        "createdAt": stub.get("createdAt") or "",
        "updatedAt": stub.get("updatedAt") or stub.get("createdAt") or "",
        "severity": stub.get("severity") or "MEDIUM",
        "status": stub.get("status") or "",
        "description": stub.get("description") or "",
        "labels": stub.get("labels") if stub.get("labels") not in (None,) else [],
    }


def merge_related_alert(stub: SingleJson, full: SingleJson | None) -> SingleJson:
    """Prefer the full getAlerts record; keep nested incident stub labels if needed.

    getIncidents `alerts { ... }` is often what we package when getAlerts(id)
    misses a related alert. Those stubs used to drop labels, so SecOps showed [].
    """
    stub = stub if isinstance(stub, dict) else {}
    if not isinstance(full, dict):
        return stub_to_alert(stub)
    merged = dict(full)
    if not record_label_tags(merged) and stub.get("labels") not in (None, "", [], {}):
        merged["labels"] = stub.get("labels")
    if not str(merged.get("vegaAlertId") or "").strip():
        vega_id = str(stub.get("vegaAlertId") or "").strip()
        if vega_id:
            merged["vegaAlertId"] = vega_id
    return merged


def _related_incident_items(alert: SingleJson) -> list[SingleJson]:
    related = alert.get("relatedIncidents") if isinstance(alert, dict) else None
    if isinstance(related, dict):
        related = [related]
    if not isinstance(related, list):
        return []
    return [item for item in related if isinstance(item, dict)]


def related_incident_ids(alert: SingleJson) -> list[str]:
    """Every incident id on the alert. The first entry is not the only link."""
    ids: list[str] = []
    for item in _related_incident_items(alert):
        identifier = str(item.get("incidentId") or item.get("id") or "").strip()
        if identifier and identifier not in ids:
            ids.append(identifier)
    return ids


def related_incident_ref(alert: SingleJson) -> tuple[str, str]:
    """Return the first related incident id and name for an alert."""
    for item in _related_incident_items(alert):
        identifier = str(item.get("incidentId") or item.get("id") or "").strip()
        if identifier:
            return identifier, str(item.get("name") or "").strip()
    return "", ""


def index_alert_records(alerts: list[SingleJson]) -> dict[str, SingleJson]:
    """Index alert records by every known alert id variant."""
    index: dict[str, SingleJson] = {}
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        for key in record_alert_ids(alert):
            index[key] = alert
    return index


def record_severity(record: SingleJson) -> str:
    """Return the Vega severity string for a record."""
    raw = str(record.get("severity") or "MEDIUM").strip().upper()
    if raw not in SEVERITY_TO_ALERT_PRIORITY:
        return "MEDIUM"
    return raw


def record_timestamp(record: SingleJson) -> str:
    """Return the best timestamp string for ordering a Vega record."""
    return str(record.get("updatedAt") or record.get("lastUpdated") or record.get("createdAt") or "")


def _flatten_entities(record: SingleJson) -> dict[str, str]:
    buckets = {
        "ip": [],
        "domain": [],
        "user": [],
        "hash": [],
        "url": [],
        "hostname": [],
    }
    type_map = {
        "ip": "ip",
        "ipv4": "ip",
        "ipv6": "ip",
        "domain": "domain",
        "user": "user",
        "username": "user",
        "email": "user",
        "hash": "hash",
        "md5": "hash",
        "sha1": "hash",
        "sha256": "hash",
        "url": "url",
        "uri": "url",
        "hostname": "hostname",
        "host": "hostname",
        "fqdn": "hostname",
    }
    blobs: list = []
    for key in ("entities", "observables", "assets"):
        value = record.get(key)
        if value:
            blobs.append(value)
    for blob in blobs:
        items = blob if isinstance(blob, list) else [blob]
        for item in items:
            if isinstance(item, str):
                continue
            if not isinstance(item, dict):
                continue
            kind = str(item.get("type") or item.get("category") or "").strip().lower()
            value = item.get("value") or item.get("name")
            bucket = type_map.get(kind)
            if bucket and value:
                text = str(value).strip()
                if text and text not in buckets[bucket]:
                    buckets[bucket].append(text)
    return {key: ",".join(values) for key, values in buckets.items() if values}


def _soar_key(key: Any) -> str:
    text = _SAFE_KEY_RE.sub("_", str(key or "").strip()).strip("_")
    if text and text[0].isdigit():
        text = f"f_{text}"
    return text[:80]


def _normalized_field_name(key: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(key or "").lower())


def _is_skipped_payload_key(key: Any) -> bool:
    text = str(key or "").strip()
    if not text or text in _SKIP_PAYLOAD_KEYS:
        return True
    return _normalized_field_name(text) in _SKIP_TIME_NORMALIZED


def _apply_event_times(event: SingleJson, start_time: int, end_time: int) -> None:
    """Keep a single StartTime/EndTime pair so SecOps does not repeat dates."""
    event["StartTime"] = start_time
    event["EndTime"] = end_time
    event.pop("start_time", None)
    event.pop("end_time", None)


def _soar_value(value: Any, *, limit: int = _MAX_EVENT_FIELD_CHARS) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        text = _safe_json(value)
    elif isinstance(value, bool):
        text = "true" if value else "false"
    else:
        text = str(value)
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text


def _has_mapped_value(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, (list, dict)) and not value:
        return False
    return True


def _set_mapped(event: SingleJson, key: str, value: Any) -> None:
    if not key or key in event or not _has_mapped_value(value):
        return
    event[key] = _soar_value(value)


def _map_api_fields(event: SingleJson, record: SingleJson, fields: tuple[tuple[str, str], ...]) -> None:
    if not isinstance(record, dict):
        return
    for api_key, event_key in fields:
        if api_key not in record:
            continue
        value = record.get(api_key)
        if api_key == "labels":
            value = _display_labels(value)
        _set_mapped(event, event_key, value)


def _apply_entity_aliases(event: SingleJson, payload: SingleJson) -> None:
    for key, value in payload.items():
        bucket = _ENTITY_ALIASES.get(str(key).strip().lower())
        if not bucket or bucket in event or not _has_mapped_value(value):
            continue
        if isinstance(value, (dict, list)):
            continue
        event[bucket] = _soar_value(value)


def _details_payload(record: SingleJson) -> str:
    """JSON snapshot of the Vega record without duplicating child events."""
    if not isinstance(record, dict):
        return _safe_json(record)
    trimmed = {}
    for key, value in record.items():
        if key in (
            SOAR_META_KEY,
            "alert_events",
            "nested_related_alerts",
            "vega_alerts",
        ):
            continue
        if key == "labels":
            trimmed[key] = _display_labels(value)
            continue
        if not _has_mapped_value(value):
            continue
        trimmed[key] = value
    if "labels" not in trimmed:
        trimmed["labels"] = []
    return _soar_value(trimmed, limit=_MAX_DETAILS_CHARS)


# Selection set from GET_ALERTS_QUERY `alerts { ... }`.
_ALERT_API_FIELDS = (
    ("vegaAlertId", "vega_alert_id"),
    ("detectionId", "detection_id"),
    ("description", "description"),
    ("status", "status"),
    ("assignee", "assignee"),
    ("assignees", "assignees"),
    ("dataSources", "data_sources"),
    ("createdAt", "created_at"),
    ("updatedAt", "updated_at"),
    ("mitre", "mitre"),
    ("relatedIncidents", "related_incidents"),
    ("detectionSource", "detection_source"),
    ("detectionDescription", "detection_description"),
    ("detectionQuery", "detection_query"),
    ("eventCount", "event_count"),
    ("isTestMode", "is_test_mode"),
    ("verdict", "verdict"),
    ("verdictReasoning", "verdict_reasoning"),
    ("escalation", "escalation"),
    ("dedupCount", "dedup_count"),
    ("comments", "comments"),
    ("labels", "labels"),
    ("skills", "skills"),
    ("actors", "actors"),
    ("targets", "targets"),
    ("href", "source_url"),
)

# Selection set from GET_INCIDENTS_QUERY `incidents { ... }`, plus timeline
# enrichment from getIncidentTimeline.
_INCIDENT_API_FIELDS = (
    ("vegaUniqueIncidentId", "vega_unique_incident_id"),
    ("createdBy", "created_by"),
    ("createdAt", "created_at"),
    ("lastUpdated", "updated_at"),
    ("investigationStatus", "investigation_status"),
    ("userStatus", "user_status"),
    ("dataSources", "data_sources"),
    ("verdict", "verdict"),
    ("verdictReasoning", "verdict_reasoning"),
    ("assignee", "assignee"),
    ("assignees", "assignees"),
    ("comments", "comments"),
    ("incidentSummary", "description"),
    ("incidentFindings", "incident_findings"),
    ("assets", "assets"),
    ("observables", "observables"),
    ("alertsCount", "alerts_count"),
    # Do not map API `alerts` onto an event field named `alerts`. SecOps
    # reserves that name for the case's alert list and drops it from Default.
    ("recommendedActions", "recommended_actions"),
    ("investigationPlan", "investigation_plan"),
    ("labels", "labels"),
    ("skills", "skills"),
    ("href", "source_url"),
    ("link", "source_url"),
    ("timeline", "timeline"),
)


def _apply_label_fields(event: SingleJson, record: SingleJson, *, copy_incident_names: bool) -> None:
    """Put this Vega record's labels on a SOAR event.

    Incident names stay on `vega_incident_label_names` for related alerts;
    they are not copied onto `labels`.
    """
    event["labels"] = _soar_value(_display_labels(record.get("labels") if isinstance(record, dict) else None))
    label_names = record_label_tags(record)
    if label_names:
        event["vega_label_names"] = ",".join(label_names)
    if not copy_incident_names:
        return
    meta = soar_meta(record)
    incident_label_names = [str(name).strip() for name in (meta.get("incident_label_tags") or []) if str(name).strip()]
    if incident_label_names:
        event["vega_incident_label_names"] = ",".join(incident_label_names)


def related_alert_rows(record: SingleJson) -> list[SingleJson]:
    """Rows for the incident event: full vega_alerts, else getIncidents stubs."""
    raw = record.get("vega_alerts") if isinstance(record, dict) else None
    if isinstance(raw, list):
        rows: list[SingleJson] = []
        for item in raw:
            if isinstance(item, dict):
                rows.append(item)
            elif str(item or "").strip():
                rows.append({"alertId": str(item).strip()})
        return rows
    rows = []
    for stub in incident_alert_stubs(record):
        summary = incident_alert_summary(stub)
        if summary:
            rows.append(summary)
    return rows


def related_alert_ids(rows: list[SingleJson]) -> list[str]:
    """Return unique alert ids from related-alert row dicts."""
    ids: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        alert_id = str(row.get("alertId") or row.get("id") or row.get("vegaAlertId") or "").strip()
        if not alert_id or alert_id in seen:
            continue
        seen.add(alert_id)
        ids.append(alert_id)
    return ids


def build_event_dict(record: SingleJson, entity_type: str, start_time: int, end_time: int) -> SingleJson:
    """Map a Vega alert or incident onto a SOAR event using API fields only.

    Empty or missing Vega values are omitted so the Default event section does
    not show null fields that were never returned by getAlerts/getIncidents.
    `labels` is always present: Vega names/colors, or `[]` when there are none.
    """
    identifier = record_id(record, entity_type)
    severity = record_severity(record)
    meta = soar_meta(record)
    incident_id = str(meta.get("incident_id") or record.get("vega_incident_id") or "").strip()
    incident_display_id = str(meta.get("incident_display_id") or record.get("vegaUniqueIncidentId") or "").strip()
    soar_alert_type = str(
        meta.get("soar_alert_type")
        or (SOAR_ALERT_TYPE_INCIDENT if entity_type == ENTITY_TYPE_INCIDENT else SOAR_ALERT_TYPE_ALERT)
    )
    event = {
        "StartTime": start_time,
        "EndTime": end_time,
        "name": case_display_name(record, entity_type),
        "device_vendor": VENDOR_NAME,
        "device_product": DEVICE_PRODUCT,
        "product": DEVICE_PRODUCT,
        "event_type": entity_type,
        "product_log_id": identifier,
        "vega_id": identifier,
        "event_class_id": identifier,
        "DeviceEventClassID": identifier,
        "Severity": severity,
        "vega_entity_type": entity_type,
        "vega_soar_alert_type": soar_alert_type,
    }
    if entity_type == ENTITY_TYPE_INCIDENT:
        # Sit next to vega_entity_type so Default shows them without scrolling
        # past the rest of the incident. Always present, including [].
        rows = related_alert_rows(record)
        alert_ids = related_alert_ids(rows)
        event["vega_related_alert_ids"] = ",".join(alert_ids) if alert_ids else "[]"
        event["vega_alerts"] = _soar_value(rows, limit=_MAX_DETAILS_CHARS)
    _set_mapped(event, "vega_incident_id", incident_id)
    if entity_type == ENTITY_TYPE_INCIDENT:
        _map_api_fields(event, record, _INCIDENT_API_FIELDS)
    else:
        _map_api_fields(event, record, _ALERT_API_FIELDS)
    _set_mapped(event, "vega_unique_incident_id", incident_display_id)
    _apply_label_fields(event, record, copy_incident_names=entity_type == ENTITY_TYPE_ALERT)
    details = _details_payload(record)
    if details:
        event["details"] = details
    event.update(_flatten_entities(record))
    _apply_recommended_action_fields(event, record)
    _apply_event_times(event, start_time, end_time)
    return event


def _try_parse_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "{[":
        return value
    try:
        return json.loads(text)
    except Exception:
        return value


def _recommended_action_items(record: SingleJson) -> list[SingleJson]:
    raw = record.get("recommendedActions")
    if raw is None:
        raw = record.get("recommended_actions")
    parsed = _try_parse_json(raw)
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return []
    items: list[SingleJson] = []
    for item in parsed:
        item = _try_parse_json(item)
        if isinstance(item, dict):
            items.append(item)
    return items


def _recommended_action_key(item: SingleJson) -> str:
    return str(item.get("actionKey") or item.get("action_key") or "").strip()


def _recommended_action_params(item: SingleJson) -> SingleJson:
    params = _try_parse_json(item.get("targetParams") or item.get("target_params") or {})
    return params if isinstance(params, dict) else {}


def _recommended_action_user(item: SingleJson) -> str:
    params = _recommended_action_params(item)
    return str(
        params.get("user_id") or params.get("userId") or params.get("email") or params.get("username") or ""
    ).strip()


def _merge_csv_values(event: SingleJson, key: str, values: list[str]) -> None:
    existing = [item.strip() for item in str(event.get(key) or "").split(",") if item.strip()]
    for value in values:
        if value and value not in existing:
            existing.append(value)
    if existing:
        event[key] = ",".join(existing)


def reset_password_users_from_payload(payload: SingleJson) -> list[str]:
    """User emails/logins from mapped fields or reset_user_password actions."""
    users: list[str] = []

    def _add(value: Any) -> None:
        for part in str(value or "").split(","):
            text = part.strip()
            if text and text not in users:
                users.append(text)

    if not isinstance(payload, dict):
        return users
    _add(payload.get("vega_reset_password_user"))
    _add(payload.get("vega_target_users"))
    records = [payload]
    details = _try_parse_json(payload.get("details"))
    if isinstance(details, dict):
        records.append(details)
    for record in records:
        for item in _recommended_action_items(record):
            if _recommended_action_key(item) != RESET_USER_PASSWORD_ACTION_KEY:
                continue
            _add(_recommended_action_user(item))
    return users


def _apply_recommended_action_fields(event: SingleJson, record: SingleJson) -> None:
    """Expose recommended-action keys and Okta reset target on the SOAR event.

    Playbooks can trigger on `vega_recommended_action_keys` / `recommended_actions`
    and read `vega_reset_password_user` / `user` for Okta reset targets.
    """
    keys: list[str] = []
    for item in _recommended_action_items(record):
        key = _recommended_action_key(item)
        if key and key not in keys:
            keys.append(key)
    if keys:
        event["vega_recommended_action_keys"] = ",".join(keys)
    reset_users = reset_password_users_from_payload(record)
    if not reset_users:
        return
    event["vega_reset_password_user"] = reset_users[0]
    _merge_csv_values(event, "user", reset_users)


def normalize_alert_event(vega_event: Any) -> SingleJson:
    """Parse getAlertsEvents rows, including JSON `fields` / `fields._raw` payloads."""
    payload = dict(vega_event) if isinstance(vega_event, dict) else {"value": vega_event}
    fields = _try_parse_json(payload.get("fields"))
    if not isinstance(fields, dict):
        return payload
    merged = dict(payload)
    raw = _try_parse_json(fields.get("_raw"))
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key not in merged or merged[key] in (None, ""):
                merged[key] = value
    for key, value in fields.items():
        if key == "_raw":
            continue
        if key not in merged or merged[key] in (None, ""):
            merged[key] = value
    merged["fields"] = fields
    return merged



def alert_priority(severity: str) -> int:
    """Map a Vega severity string to a SecOps alert priority integer."""
    return SEVERITY_TO_ALERT_PRIORITY.get(str(severity).upper(), 60)

from .alert_event_mapping import build_vega_alert_event_dict
