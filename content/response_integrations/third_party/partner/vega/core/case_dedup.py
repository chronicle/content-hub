"""Helpers for Vega case dedup and Max Alerts in Case slot accounting."""

from __future__ import annotations

import re
from typing import Any

from .case_insight import (
    extract_incident_id_from_ticket,
    parse_alert_additional_properties,
)
from .constants import VENDOR_NAME
from .mapping import incident_grouping_id

_INSTANCE_PATH_RE = re.compile(r"projects/[^/]+/locations/[^/]+/instances/[^/]+")
_SDK_CONFIG_FALLBACK_TOKENS = (
    "/projects/project/",
    "/locations/location/",
    "/instances/instance/",
)


def ingested_signal_count(incident_id: str, ingested_set: set[str]) -> int:
    incident_id = str(incident_id or "").strip()
    if not incident_id:
        return 0
    prefix = f"{incident_id}:"
    return sum(1 for key in ingested_set if str(key).startswith(prefix))


def remaining_ingest_slots(incident_id: str, ingested_set: set[str], max_alerts: int) -> int:
    cap = max(0, int(max_alerts))
    return max(0, cap - ingested_signal_count(incident_id, ingested_set))


def can_merge_cases(primary_alerts: int, duplicate_alerts: int, max_alerts: int) -> bool:
    cap = max(0, int(max_alerts))
    if cap <= 0:
        return False
    return int(primary_alerts) + int(duplicate_alerts) <= cap


def grouping_key_from_alert(alert: Any) -> str:
    if not isinstance(alert, dict):
        props = parse_alert_additional_properties(getattr(alert, "additional_properties", None))
        candidates = (
            getattr(alert, "source_grouping_identifier", None),
            getattr(alert, "alert_group_identifier", None),
            getattr(alert, "ticket_id", None),
            getattr(alert, "display_id", None),
            props.get("SourceGroupingIdentifier"),
            props.get("source_grouping_identifier"),
            props.get("sourceGroupingIdentifier"),
            props.get("ticket_id"),
            props.get("ticketId"),
        )
    else:
        props = alert.get("additional_properties") or alert.get("additionalProperties") or {}
        if not isinstance(props, dict):
            props = parse_alert_additional_properties(props)
        candidates = (
            alert.get("source_grouping_identifier"),
            alert.get("sourceGroupingIdentifier"),
            alert.get("alert_group_identifier"),
            alert.get("alertGroupIdentifier"),
            alert.get("ticket_id"),
            alert.get("ticketId"),
            alert.get("display_id"),
            alert.get("displayId"),
            props.get("SourceGroupingIdentifier"),
            props.get("source_grouping_identifier"),
            props.get("sourceGroupingIdentifier"),
            props.get("ticket_id"),
            props.get("ticketId"),
        )

    prefix = f"{VENDOR_NAME}:incident:".lower()
    for raw in candidates:
        text = str(raw or "").strip()
        if not text:
            continue
        if text.lower().startswith(prefix) and ":signal:" not in text.lower():
            incident_id = extract_incident_id_from_ticket(text) or text.split(":", 2)[-1]
            if incident_id:
                return incident_grouping_id(incident_id)
        incident_id = extract_incident_id_from_ticket(text)
        if incident_id:
            return incident_grouping_id(incident_id)
    return ""


def resolve_cases_merge_url(soar_job: Any) -> tuple[str | None, str]:
    """Build Chronicle v1beta ``cases:merge`` URL from SDK config, or ``(None, reason)``."""
    try:
        fmt = soar_job.sdk_config.one_platform_api_root_uri_format
    except AttributeError:
        return None, "sdk_config.one_platform_api_root_uri_format unavailable"
    if not fmt:
        return None, "sdk_config.one_platform_api_root_uri_format unavailable"
    try:
        base = fmt.format("v1beta")
    except Exception as exc:
        return None, f"sdk_config format failed: {exc}"
    if _INSTANCE_PATH_RE.search(base) and not any(t in base for t in _SDK_CONFIG_FALLBACK_TOKENS):
        return base.rstrip("/") + "/cases:merge", "sdk_config auto-detect"
    return None, "sdk_config missing or placeholder instance path"
