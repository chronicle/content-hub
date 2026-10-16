from __future__ import annotations

import html
import ipaddress
import json
import re
from typing import Any

from soar_sdk.SiemplifyDataModel import EntityTypes

from .houdin_constants import APP_ROOT, ENRICHMENT_PREFIX

# Entity types Houdin can scan. ADDRESS is kept only when the address is public.
SCANNABLE_ENTITY_TYPES = {
    EntityTypes.ADDRESS,
    EntityTypes.URL,
    EntityTypes.HOSTNAME,
    EntityTypes.FILEHASH,
    "DOMAIN",
}


def is_public_ip(value: str) -> bool:
    try:
        return ipaddress.ip_address(value).is_global
    except ValueError:
        return False


def is_scannable_entity(entity: Any) -> bool:
    """URL, domain, hostname, file hash, or a public IP address."""
    entity_type = getattr(entity, "entity_type", None)
    if entity_type not in SCANNABLE_ENTITY_TYPES:
        return False
    if entity_type == EntityTypes.ADDRESS:
        return is_public_ip(entity.identifier)
    if entity_type == EntityTypes.HOSTNAME:
        # Internal machine names carry no dot; Houdin has nothing to say about them.
        return "." in entity.identifier
    return True


def scan_link(scan_id: str) -> str:
    """The scan in the Houdin app."""
    return f"{APP_ROOT}/scans/{scan_id.removeprefix('houdin-')}"


def verdict_of(document: dict[str, Any]) -> dict[str, Any]:
    """The MesmerAI verdict of a scan document, flattened for messages and enrichment.

    Every key is present; a scan whose verdict is missing (the MesmerAI modules
    were not part of the scan, or the account has no verdict access) has None
    for score and empty strings elsewhere.
    """
    mesmer = ((document.get("scanResults") or {}).get("mesmer") or {}).get("result") or {}
    if "error" in mesmer:
        mesmer = {}
    confidence = mesmer.get("confidence") or {}
    score = mesmer.get("globalScore")
    if not isinstance(score, (int, float)):
        score = None
    return {
        "score": score,
        "confidence": str(confidence.get("level") or ""),
        "confidence_reason": str(confidence.get("reason") or ""),
        "summary": str(mesmer.get("summary") or ""),
        "tags": [str(t.get("value")) for t in mesmer.get("tags") or [] if isinstance(t, dict) and t.get("value")],
        "related": [
            str(r.get("value")) for r in mesmer.get("relatedIOCs") or [] if isinstance(r, dict) and r.get("value")
        ],
        "unrecorded": bool(mesmer.get("unrecorded")),
        "sources": [s for s in document.get("scanOn") or [] if s not in ("mesmer", "mesmer-summary")],
        "scan_id": str(document.get("scanID") or ""),
        "scan_time": str(document.get("scanTime") or ""),
        "artifact": str(document.get("artifact") or ""),
        "ioc_type": str(document.get("iocType") or ""),
    }


def enrichment_fields(document: dict[str, Any]) -> dict[str, str]:
    """The entity properties written by Enrich Entities, all prefixed with the integration name."""
    verdict = verdict_of(document)
    fields = {
        "Threat_Score": "" if verdict["score"] is None else str(verdict["score"]),
        "Confidence": verdict["confidence"],
        "Confidence_Reason": verdict["confidence_reason"],
        "AI_Analysis": verdict["summary"],
        "Tags": ", ".join(verdict["tags"]),
        "Related_IOCs": ", ".join(verdict["related"][:5]),
        "Sources": ", ".join(verdict["sources"]),
        "Scan_ID": verdict["scan_id"],
        "Scan_Link": scan_link(verdict["scan_id"]) if verdict["scan_id"] else "",
        "Scan_Time": verdict["scan_time"],
    }
    if verdict["unrecorded"]:
        fields["Unrecorded"] = "true"
    return {f"{ENRICHMENT_PREFIX}_{key}": value for key, value in fields.items() if value != ""}


def verdict_line(document: dict[str, Any]) -> str:
    """One line for output messages: '8/10, high confidence: Malicious hosting, Trojan installer'."""
    verdict = verdict_of(document)
    if verdict["score"] is None:
        return "no MesmerAI verdict"
    line = f"{verdict['score']}/10"
    if verdict["confidence"]:
        line += f", {verdict['confidence']} confidence"
    if verdict["unrecorded"]:
        line += " (no source holds a record of it)"
    if verdict["tags"]:
        line += ": " + ", ".join(verdict["tags"][:4])
    return line


BULLET = re.compile(r"^\s*[-*]\s+")


def markdown_to_html(text: str) -> str:
    """The summary is Markdown; bold, italics, inline code, bullet lines and paragraphs are enough for an insight."""
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"`([^`\n]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*\n]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"(^|[^*])\*([^*\n]+)\*(?!\*)", r"\1<i>\2</i>", escaped)
    blocks = []
    for block in re.split(r"\n{2,}", escaped.strip()):
        lines = block.split("\n")
        if lines and all(BULLET.match(line) for line in lines):
            items = "".join("<li>" + BULLET.sub("", line) + "</li>" for line in lines)
            blocks.append(f"<ul>{items}</ul>")
        else:
            blocks.append("<br/>".join(lines))
    return "<br/><br/>".join(blocks)


def insight_content(document: dict[str, Any]) -> str:
    """The entity insight: verdict line, summary, sources, link."""
    verdict = verdict_of(document)
    parts = [f"<b>Threat score: {html.escape(verdict_line(document), quote=False)}</b>"]
    if verdict["summary"]:
        parts.append(markdown_to_html(verdict["summary"]))
    if verdict["sources"]:
        parts.append("Sources: " + ", ".join(verdict["sources"]))
    if verdict["scan_id"]:
        link = scan_link(verdict["scan_id"])
        parts.append(f'<a href="{link}" target="_blank">Open in Houdin</a>')
    return "<br/><br/>".join(parts)


def parse_scanners(raw: Any) -> list[str] | None:
    """The Scanners parameter is a comma list (a JSON array string is accepted too); return a list or None."""
    if raw is None:
        return None
    if isinstance(raw, list):
        return [str(s) for s in raw]
    text = str(raw).strip()
    if not text:
        return None
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = []
        items = [str(s) for s in parsed] if isinstance(parsed, list) else []
    else:
        items = [s.strip() for s in text.split(",") if s.strip()]
    return items or None


def parse_threshold(raw: Any, default: int) -> int | None:
    """The suspicious threshold: an integer 0 to 10, None to disable, the default when blank."""
    if raw is None:
        return default
    text = str(raw).strip()
    if not text:
        return default
    if text.lower() in ("none", "off", "disable", "disabled"):
        return None
    try:
        value = int(float(text))
    except ValueError as error:
        raise ValueError(f"Suspicious Threshold must be a number between 0 and 10, not {text!r}") from error
    if not 0 <= value <= 10:
        raise ValueError(f"Suspicious Threshold must be between 0 and 10, not {value}")
    return value


def load_state(raw: Any) -> dict[str, Any] | None:
    """The additional_data an async action handed to its previous run; None on the first run."""
    if raw in (None, "", True, False):
        return None
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None
