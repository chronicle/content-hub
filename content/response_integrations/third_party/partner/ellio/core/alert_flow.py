"""Alert-flow context shared by the enrichment actions.

The direction (source/destination) and the from->to flow come from the ALERT
relations (DomainRelationInfo.from_identifier -> to_identifier), not from ELLIO.
Used by both CBS Lookup and Enrich IP so their insight cards stay consistent.
"""
from __future__ import annotations

from typing import Any

from .insight_ui import GUIDE_LINE, id_chip


def relations_for(siemplify: Any, ip: str) -> tuple[str, list[tuple[str, str]]]:
    """Role and flows for `ip` from the alert relations.

    Args:
        siemplify: The SiemplifyAction instance.
        ip: The IP entity identifier to look up.

    Returns:
        A (role, flows) tuple: role is 'source' / 'destination' /
        'source & destination' / ''; flows is a list of distinct
        (from_identifier, to_identifier) pairs (the counterpart may be an IP,
        hostname, or domain).
    """
    alerts = []
    try:
        if siemplify.current_alert:
            alerts = [siemplify.current_alert]
    except Exception as error:  # noqa: BLE001
        siemplify.LOGGER.info(f"No current alert available: {error}")
        alerts = []
    if not alerts:
        try:
            alerts = siemplify.case.alerts or []
        except Exception as error:  # noqa: BLE001
            siemplify.LOGGER.info(f"No case alerts available: {error}")
            alerts = []
    roles, flows, seen = set(), [], set()
    for alert in alerts:
        for rel in getattr(alert, "relations", None) or []:
            f = getattr(rel, "from_identifier", None)
            t = getattr(rel, "to_identifier", None)
            if ip not in (f, t):
                continue
            if f == ip:
                roles.add("source")
            if t == ip:
                roles.add("destination")
            if (f, t) not in seen:
                seen.add((f, t))
                flows.append((f or "?", t or "?"))
    if {"source", "destination"} <= roles:
        role = "source & destination"
    elif "source" in roles:
        role = "source"
    elif "destination" in roles:
        role = "destination"
    else:
        role = ""
    return role, flows


def flow_footer_html(ip: str, flows: list[tuple[str, str]], separator: bool = True) -> str:
    """Theme-adaptive footer: 'In this alert: src X -> dst Y'.

    Args:
        ip: The IP the footer is rendered for.
        flows: Distinct (from_identifier, to_identifier) pairs.
        separator: Draw the top rule; pass False when the caller draws its own
            rule above the footer (e.g. a full-width button carries it).

    Returns:
        The footer HTML, or an empty string when there are no flows.
    """
    if not flows:
        return ""
    rows = []
    ns = '-webkit-user-select:none;user-select:none;'   # labels excluded from copy
    for f, t in flows[:3]:
        # IPs as identifier chips (monospace, outlined, atomic-select); per guideline
        rows.append(f'<span style="opacity:.55;{ns}">src</span> {id_chip(f)} '
                    f'<span style="opacity:.5;{ns}">&rarr;</span> '
                    f'<span style="opacity:.55;{ns}">dst</span> {id_chip(t)}')
    more = (f' <span style="opacity:.5">+{len(flows) - 3} more</span>'
            if len(flows) > 3 else "")
    lead = (f"margin-top:10px;padding-top:7px;border-top:1px solid {GUIDE_LINE};"
            if separator else "margin-top:6px;")
    return (f'<div style="{lead}font-size:11px;line-height:1.5;overflow-wrap:anywhere;">'
            f'<span style="opacity:.6;{ns}">In this alert:</span> '
            + "<br>".join(rows) + more + "</div>")
