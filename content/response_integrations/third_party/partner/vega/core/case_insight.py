"""Build SecOps case insight payloads from Vega incident records."""

from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

from .constants import DEVICE_PRODUCT, VENDOR_NAME
from .mapping import incident_alert_stubs, rank_signals, record_name


def _insight_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, default=str)
    else:
        text = str(value)
    return html.escape(text)


def _ai_verdict_text(record: SingleJson) -> str:
    verdict = str(record.get("verdict") or "").strip()
    reasoning = str(record.get("verdictReasoning") or "").strip()
    if verdict and reasoning:
        return f"{verdict} — {reasoning}"
    return verdict or reasoning


def build_case_description(incident: SingleJson) -> str:
    """Case Description: Vega verdict (and reasoning) only."""
    record = incident if isinstance(incident, dict) else {}
    return _ai_verdict_text(record)


def _top_signals(record: SingleJson, *, limit: int = 10) -> list[str]:
    stubs = [dict(item) for item in incident_alert_stubs(record) if isinstance(item, dict)]
    ranked = rank_signals(stubs, limit) if stubs else []
    rows: list[str] = []
    for item in ranked:
        alert_id = str(item.get("alertId") or item.get("id") or "").strip()
        name = record_name(item)
        rows.append(f"{alert_id} — {name}" if alert_id else name)
    return rows


def build_incident_insight(
    incident: SingleJson,
    *,
    signals_in_case: int,
    total_signals: int | None = None,
) -> str:
    """HTML key/value insight for a Vega incident case (rendered on case wall)."""
    record = incident if isinstance(incident, dict) else {}
    total = total_signals
    if total is None:
        try:
            total = int(record.get("alertsCount") or 0)
        except (TypeError, ValueError):
            total = 0
    total = max(int(total or 0), int(signals_in_case or 0))
    in_case = max(0, int(signals_in_case or 0))

    incident_id = str(
        record.get("vegaUniqueIncidentId") or record.get("id") or record.get("incidentId") or ""
    ).strip()
    link = str(record.get("link") or record.get("href") or "").strip()
    # shortcut: Vega API exposes one verdict; map it as AI Verdict until analyst verdict exists
    ai_verdict = _ai_verdict_text(record)
    rows: list[tuple[str, Any]] = [
        ("Vega Incident ID", incident_id),
        ("Vega Incident Link", link),
        ("Vega Verdict", ai_verdict),
        ("Vega Incident Severity", record.get("severity")),
        ("Vega Investigation Status", record.get("investigationStatus")),
        ("Vega User Status", record.get("userStatus")),
        ("Vega Signals", f"{total} total, {in_case} in case"),
        ("Incident Summary", record.get("incidentSummary")),
        ("Incident Findings", record.get("incidentFindings")),
        ("Recommended Actions", record.get("recommendedActions")),
        ("Top Signals", _top_signals(record)),
        ("Typed Assets", record.get("typedAssets")),
        ("Typed Observables", record.get("typedObservables")),
        ("Comments", record.get("comments")),
        ("Labels", record.get("labels")),
    ]

    body_parts: list[str] = []
    for key, value in rows:
        if value in (None, "", [], {}):
            continue
        body_parts.append(f"<strong>{html.escape(key)}: </strong>{_insight_value(value)}<br/>")
    if link:
        safe_link = html.escape(link, quote=True)
        body_parts.append(
            f"<p>Open in Vega: <a href='{safe_link}' target='_blank'>{html.escape(link)}</a></p>"
        )
    return f"<p>{''.join(body_parts)}</p>"


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


def extract_signal_id_from_ticket(ticket_id: str) -> str:
    """Parse ``Vega:incident:<incident_id>:signal:<alert_id>`` → alert/signal id."""
    text = str(ticket_id or "").strip()
    marker = ":signal:"
    lower = text.lower()
    idx = lower.find(marker)
    if idx < 0:
        return ""
    rest = text[idx + len(marker) :].strip()
    # Optional packaging suffixes like ``:test 10`` after the alert id.
    if ":test" in rest.lower():
        rest = rest[: rest.lower().index(":test")]
    return rest.strip().strip(":")


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
