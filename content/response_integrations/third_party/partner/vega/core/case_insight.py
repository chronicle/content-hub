"""Build SecOps case insight payloads from Vega incident records."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

from .constants import DEVICE_PRODUCT, VENDOR_NAME

# Flat key/value insight fields (incident → case). Skip bulky nested blobs.
# incidentSummary is written to Case Description by SyncAlerts, not insight.
_INSIGHT_KEYS = (
    "id",
    "vegaUniqueIncidentId",
    "name",
    "severity",
    "userStatus",
    "investigationStatus",
    "verdict",
    "verdictReasoning",
    "incidentFindings",
    "createdAt",
    "lastUpdated",
    "link",
    "href",
    "alertsCount",
    "dataSources",
    "assets",
)


def build_incident_insight(
    incident: SingleJson,
    *,
    signals_in_case: int,
    total_signals: int | None = None,
) -> str:
    """JSON key/value insight string for a Vega incident case.

    Includes overflow summary like ``"312 signals, 30 in case"``.
    """
    payload: dict[str, Any] = {}
    record = incident if isinstance(incident, dict) else {}
    for key in _INSIGHT_KEYS:
        value = record.get(key)
        if value in (None, "", [], {}):
            continue
        payload[key] = value
    total = total_signals
    if total is None:
        try:
            total = int(record.get("alertsCount") or 0)
        except (TypeError, ValueError):
            total = 0
    total = max(int(total or 0), int(signals_in_case or 0))
    in_case = max(0, int(signals_in_case or 0))
    payload["signals_summary"] = f"{total} signals, {in_case} in case"
    payload["signals_in_case"] = in_case
    payload["signals_total"] = total
    link = str(record.get("link") or record.get("href") or "").strip()
    if link:
        payload["vega_incident_link"] = link
    return json.dumps(payload, ensure_ascii=False, default=str)


def extract_incident_id_from_ticket(ticket_id: str) -> str:
    """Parse ``Vega:incident:<incident_id>:signal:<alert_id>`` → incident id."""
    text = str(ticket_id or "").strip()
    prefix = "Vega:incident:"
    if not text.lower().startswith(prefix.lower()):
        return ""
    rest = text[len(prefix) :]
    if ":signal:" in rest:
        return rest.split(":signal:", 1)[0].strip()
    # Grouping id form without signal suffix.
    return rest.split(":", 1)[0].strip() if rest else ""


def parse_alert_additional_properties(raw: Any) -> dict[str, Any]:
    """AlertCard.additional_properties is a JSON string on SecOps overview."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def incident_ids_from_soar_alert(alert: Any) -> list[str]:
    """Vega incident ids carried on one SecOps alert card."""
    props = parse_alert_additional_properties(getattr(alert, "additional_properties", None))
    vendor = str(
        getattr(alert, "device_vendor", None)
        or props.get("device_vendor")
        or props.get("deviceVendor")
        or ""
    ).strip()
    product = str(
        getattr(alert, "device_product", None)
        or props.get("device_product")
        or props.get("deviceProduct")
        or ""
    ).strip()
    is_vega = (
        vendor.casefold() == VENDOR_NAME.casefold()
        or product.casefold() == DEVICE_PRODUCT.casefold()
    )
    if vendor and product and not is_vega:
        return []
    found: list[str] = []
    seen: set[str] = set()

    def _add(value: str) -> None:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            found.append(text)

    for candidate in (
        getattr(alert, "ticket_id", None),
        getattr(alert, "display_id", None),
        getattr(alert, "alert_group_identifier", None),
        getattr(alert, "source_grouping_identifier", None),
        getattr(alert, "identifier", None),
        props.get("ticket_id"),
        props.get("ticketId"),
        props.get("SourceGroupingIdentifier"),
        props.get("source_grouping_identifier"),
        props.get("sourceGroupingIdentifier"),
        props.get("alertGroupIdentifier"),
        props.get("alert_group_identifier"),
    ):
        _add(extract_incident_id_from_ticket(str(candidate or "")))
    plain = str(props.get("vega_incident_id") or "").strip()
    if plain:
        _add(extract_incident_id_from_ticket(plain) or plain)
    return found
