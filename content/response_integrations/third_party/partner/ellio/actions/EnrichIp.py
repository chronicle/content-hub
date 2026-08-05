"""ELLIO - Enrich IP

For each IP entity (and/or IPs given as a parameter), look up ELLIO threat context
via the live ELLIO CTI API, enrich the entity, add an insight card, and return a JSON
result.

Case priority: the action only RECOMMENDS a priority - it never sets one. A malicious
verdict recommends High; every other classification (promiscuous/unknown/benign) leaves
the case priority untouched. The recommendation is returned as the script result
`recommended_priority` ("High" or "None") for a playbook to apply via the built-in
Change Priority action.
"""
from __future__ import annotations

import html
import re
from collections.abc import Callable
from datetime import date
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.action_utils import collect_target_ips, config_reader
from ..core.alert_flow import GUIDE_LINE, flow_footer_html, relations_for
from ..core.constants import (
    CLASSIFICATION_PRIORITY,
    DEFAULT_ELLIO_API_ROOT,
    ENRICH_PREFIX,
    INTEGRATION_NAME,
)
from ..core.ellio_manager import EllioManager, EllioManagerError
from ..core.insight_ui import ACCENT, fingerprint, id_chip, status_pill

SCRIPT_NAME = "Enrich IP"


PLATFORM_IP_URL = "https://platform.ellio.tech/dashboard/cti/ip/{ip}"
_DOT = "·"        # middle-dot separator
_ELLIPSIS = "…"
_MORE = re.compile(r"^\(\+(\d+) more\)$")


def _items(r: dict[str, Any], key: str) -> tuple[list[str], int]:
    """Split a pipe-joined record field, honouring the '(+N more)' cap sentinel.

    Args:
        r: The normalized lookup record.
        key: The record field to split.

    Returns:
        A (values, extra_count) tuple; extra_count carries the sentinel's N.
    """
    vals = [x for x in (r.get(key) or "").split("|") if x]
    extra = 0
    if vals and _MORE.match(vals[-1]):
        extra = int(_MORE.match(vals[-1]).group(1))
        vals = vals[:-1]
    return vals, extra


def _rel(ds: str) -> str:
    """Relative recency, e.g. '2026-05-26' -> '27d ago'.

    Args:
        ds: A 'YYYY-MM-DD' date string.

    Returns:
        The relative label, or the input unchanged when it does not parse.
    """
    try:
        y, m, d = (int(x) for x in ds.split("-"))
        n = (date.today() - date(y, m, d)).days
    except (ValueError, TypeError, AttributeError):
        return ds
    if n <= 0:
        return "today"
    if n == 1:
        return "yesterday"
    if n < 30:
        return f"{n}d ago"
    if n < 365:
        return f"{n // 30}mo ago"
    return f"{n // 365}y ago"


def _cut(x: str, n: int) -> str:
    """Truncate to `n` characters with a trailing ellipsis.

    Args:
        x: The value to truncate.
        n: The maximum length in characters.

    Returns:
        The possibly-truncated string.
    """
    x = str(x)
    return x if len(x) <= n else x[:n - 1] + _ELLIPSIS


def _list(items: list[Any], extra: int, cap: int, render: Callable[[Any], str]) -> str:
    """Render up to `cap` items with a trailing '+N' for the rest.

    Args:
        items: The values to render.
        extra: Additional count carried by the manager's '(+N more)' sentinel.
        cap: Maximum items rendered before the '+N' suffix.
        render: Callable that renders one item to HTML.

    Returns:
        The rendered HTML.
    """
    shown = items[:cap]
    rest = (len(items) - len(shown)) + extra
    out = "".join(render(x) for x in shown)
    if rest:
        out += f'<span style="opacity:.5;font-size:11px;">+{rest}</span>'
    return out


def _row(label: str, value: str) -> str:
    """Inline-labelled row: a muted, non-selectable label plus chips/value.

    Args:
        label: The row label.
        value: The row content HTML.

    Returns:
        The row HTML.
    """
    return (f'<div style="margin:3px 0;font-size:11px;">'
            f'<span style="opacity:.5;-webkit-user-select:none;user-select:none;">{label}</span> '
            f'{value}</div>')


def _mono(text: str) -> str:
    """Monospace value that selects atomically (one click copies the whole value).

    Args:
        text: The value to render.

    Returns:
        The value HTML.
    """
    return (f'<span style="font-family:monospace;-webkit-user-select:all;user-select:all;">'
            f'{html.escape(text)}</span>')


def _insight_html(r: dict[str, Any], footer: str = "") -> str:
    """ELLIO threat card HTML for a lookup record.

    Classification pill, then rDNS, first/last seen, CVEs, detections, ports,
    MuonFP/JA3/JA4, and observed HTTP/UA as chips. Every value comes from the
    ELLIO API; each section renders only when its field is present.

    Args:
        r: The normalized lookup record.
        footer: Optional pre-rendered alert-flow footer HTML.

    Returns:
        The insight-card HTML.
    """
    cls = (r.get("classification") or "unknown").lower()
    ip = r.get("ip", "")

    # verdict row: classification status pill + context signals
    meta = []
    if r.get("spoofable") is False:
        meta.append("non-spoofable")
    if r.get("country"):
        meta.append(html.escape(r["country"]))
    if r.get("actor") and r["actor"].lower() != "unknown":
        meta.append("actor " + html.escape(r["actor"]))
    meta_str = (" " + _DOT + " ").join(meta)
    verdict = (f'<div style="margin:6px 0 8px;">{status_pill(cls, cls)}'
               f'<span style="opacity:.6;font-size:11px;">{meta_str}</span></div>')

    body = ""
    if r.get("rdns"):
        body += _row("rDNS", _mono(_cut(r["rdns"], 46)))
    # first -> last seen, with the relative recency kept alongside
    fs, ls = r.get("first_seen", ""), r.get("last_seen", "")
    if fs or ls:
        seen = _mono(fs or "?")
        if ls:
            seen += f' &rarr; {_mono(ls)} <span style="opacity:.55;">{_DOT} {_rel(ls)}</span>'
        body += _row("Seen", seen)

    # CVEs (identifier chips, straight from the API `cve` field)
    cves, cve_extra = _items(r, "cve")
    if cves:
        body += _row("CVE", _list(cves, cve_extra, 8, lambda c: id_chip(c)))

    # detections: the ELLIO detection-tag names as chips, in API order
    tags, tag_extra = _items(r, "tags")
    if tags:
        body += _row("Detections", _list(tags, tag_extra, 8, lambda t: id_chip(_cut(t, 40), mono=False)))

    # ports (identifier chips)
    ports, p_extra = _items(r, "ports")
    if ports:
        body += _row("Ports", _list(ports, p_extra, 12, lambda p: id_chip(p)))

    # fingerprints: MuonFP / JA3 / JA4 - text label + segment-coloured value pills
    # that flow/wrap like the detection chips (up to 3, then +N)
    for fmt, key in (("MuonFP", "muonfp"), ("JA3", "ja3"), ("JA4", "ja4")):
        fps, fp_extra = _items(r, key)
        if fps:
            body += _row(fmt, _list(fps, fp_extra, 3, lambda v, f=fmt: fingerprint(f, v)))

    # observed HTTP paths / user agents (identifier chips, truncated)
    paths, path_extra = _items(r, "http_path")
    if paths:
        body += _row("HTTP", _list(paths, path_extra, 2, lambda p: id_chip(_cut(p, 38))))
    uas, ua_extra = _items(r, "http_user_agent")
    if uas:
        body += _row("UA", _list(uas, ua_extra, 2, lambda u: id_chip(_cut(u, 38), mono=False)))

    link = (f'<a href="{PLATFORM_IP_URL.format(ip=html.escape(ip))}" target="_blank" '
            f'style="display:block;width:100%;box-sizing:border-box;text-align:center;'
            f'background:{ACCENT};color:#ffffff;padding:7px 12px;'
            f'border-radius:4px;text-decoration:none;font-size:12px;font-weight:600;">'
            f'View {html.escape(ip)} in ELLIO Platform</a>')
    # button + flow footer pinned to the card bottom (margin-top:auto); the separator
    # sits on this group above the full-width button (footer is passed separator=False).
    bottom = (f'<div style="margin-top:auto;padding-top:8px;border-top:1px solid {GUIDE_LINE};">'
              f'{link}{footer}</div>')
    return (
        '<div style="font-family:Arial,Helvetica,sans-serif;font-size:13px;">'
        '<div style="font-size:15px;font-weight:bold;">ELLIO: Threat Intelligence</div>'
        f'{verdict}{body}{bottom}</div>')


@output_handler
def main() -> None:
    """Enrich IP entities with ELLIO threat-intelligence context."""
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    cfg = config_reader(siemplify)
    ellio_api_root = cfg(param_name="API Root", default_value=DEFAULT_ELLIO_API_ROOT, input_type=str)
    ellio_api_key = cfg(param_name="API Key", is_mandatory=True, input_type=str)
    verify_ssl = cfg(param_name="Verify SSL", default_value=True, input_type=bool)

    ip_csv = extract_action_param(siemplify, param_name="IP Addresses", is_mandatory=False,
                                  input_type=str, default_value="", print_value=True)
    create_insight = extract_action_param(siemplify, param_name="Create Insight",
                                          default_value=True, input_type=bool, print_value=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    manager = EllioManager(ellio_api_root=ellio_api_root, ellio_api_key=ellio_api_key, verify_ssl=verify_ssl)

    target_ips, entity_ips, skipped = collect_target_ips(siemplify, ip_csv)
    if skipped:
        siemplify.LOGGER.info(f"Skipped non-public/internal addresses: {', '.join(skipped)}")

    json_results: dict[str, dict[str, Any]] = {}
    enriched_entities = []
    found, not_found, errored, errors = [], [], [], []
    recommended = None   # set to "High" only when a malicious IP is found

    for ip in target_ips:
        try:
            record = manager.lookup_ip(ip)
        except EllioManagerError as error:
            siemplify.LOGGER.error(f"Lookup failed for {ip}: {error}")
            errored.append(ip)
            errors.append(str(error))
            continue
        if not record:
            not_found.append(ip)
            continue

        classification = (record.get("classification") or "").lower()
        # only a malicious verdict recommends a case priority (-> High); every other
        # classification leaves the case priority untouched (no recommendation)
        priority = CLASSIFICATION_PRIORITY.get(classification)
        if priority:
            record["recommended_priority"] = priority
            recommended = priority

        json_results[ip] = record
        found.append(ip)

        # role + flow in the alert (from -> to) — from the alert relations, not ELLIO
        direction, flows = relations_for(siemplify, ip)

        entity = entity_ips.get(ip)
        if entity is not None:
            # keep False (e.g. spoofable) - only drop empty values
            entity.additional_properties.update({
                f"{ENRICH_PREFIX}{k}": v for k, v in record.items() if v not in (None, "")
            })
            if direction:
                entity.additional_properties[f"{ENRICH_PREFIX}direction"] = direction
            entity.is_enriched = True
            if classification in ("malicious", "promiscuous"):
                entity.is_suspicious = True
            # Append mode: add a fresh insight card each run (always reflects the
            # latest lookup). Gate re-runs at the playbook level to avoid pile-up.
            if create_insight:
                siemplify.add_entity_insight(
                    entity, _insight_html(record, flow_footer_html(ip, flows, separator=False)))
            enriched_entities.append(entity)

    if enriched_entities:
        siemplify.update_entities(enriched_entities)

    # The action never changes the case priority itself; it only returns a recommended
    # priority ("High" when a malicious IP is found, else "None") for a playbook to apply.
    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    if found:
        result_value = recommended or "None"
        extra = (f" (recommended case priority: {recommended} - malicious IP found)"
                 if recommended else "")
        output_message = (f"Enriched {len(found)} IP(s) with ELLIO context{extra}. "
                          f"Found: {', '.join(found)}.")
        if not_found:
            output_message += f" Not in ELLIO: {', '.join(not_found)}."
        if errored:
            output_message += f" Lookup errors: {', '.join(errored)}."
        status = EXECUTION_STATE_COMPLETED
    elif errored:
        # Nothing resolved and the API returned errors - a connection/auth failure, not a
        # genuine "not in ELLIO" result. Fail so a playbook can branch on it.
        result_value = "None"
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {errors[0]}'
        status = EXECUTION_STATE_FAILED
    else:
        result_value = "None"
        output_message = "No IP addresses were found in ELLIO threat intelligence."
        status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
