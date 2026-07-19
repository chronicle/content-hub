"""ELLIO - CBS Lookup.

Classify IP entities (and/or IPs given as a parameter) against ELLIO Common
Business Services via the ELLIO API (GET /v1/cbs/lookup?ip=). For each matched IP
the action enriches the entity with the cloud/CDN/SaaS context (provider, type,
service, region, cbs_ids, cidr) and adds a separate insight card.
"""
from __future__ import annotations

import html
from typing import Any

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.action_utils import collect_target_ips, config_reader
from ..core.alert_flow import flow_footer_html, relations_for
from ..core.constants import CBS_ENRICH_PREFIX, DEFAULT_ELLIO_API_ROOT, INTEGRATION_NAME
from ..core.ellio_manager import EllioManager, EllioManagerError
from ..core.insight_ui import GUIDE_LINE

SCRIPT_NAME = "CBS Lookup"

# --- insight card -----------------------------------------------------------
# The IP carries a LIST of labels, each a FULL hierarchy path. The card merges
# them into a faithful directory tree (trie of the full paths, one node per
# segment, shared prefixes collapsed) under category-coloured provider pills.
# No outer card chrome: the SOAR insight panel already provides it and the entity
# (IP) header. CSS-indented nested divs with left guide-lines wrap long labels.
# Top-level CBS category (first label segment) -> (short label, accent, pill bg).
# The six roots are the names of the /v1/cbs/node root children (the labels are
# built from those node names, so the keys must match exactly).
# Theme note: SecOps has light + dark mode. The card adapts WITHOUT JS/<style>:
# primary text omits `color` so it INHERITS the panel's theme colour; muted text
# uses opacity; guide lines use a semi-transparent rgba; accents/pills use
# medium/saturated tones that read on both light and dark. (accent = 600 swatch
# for the dot+label; pill bg = darker 800 swatch with white text.)
_CAT = {
    "Cloud Providers": ("Cloud", "#1E88E5", "#0277BD"),
    "Content Delivery Networks (CDNs)": ("CDN", "#00897B", "#00695C"),
    "Software as a Service (SaaS)": ("SaaS", "#8E24AA", "#6A1B9A"),
    "Internet Service Providers": ("ISP", "#FB8C00", "#EF6C00"),
    "Security Services": ("Security", "#E53935", "#C62828"),
    "Web Crawlers & Bots": ("Crawler", "#43A047", "#2E7D32"),
}
_UNKNOWN = ("#78909C", "#546E7A")   # accent, pill bg for unmapped categories


def _cat_of(root: str) -> tuple[str, str, str]:
    """Category display attributes.

    Known categories use a curated colour; an unmapped category shows its own
    root name (not a generic 'Other').

    Args:
        root: The top-level CBS category name.

    Returns:
        A (short label, accent colour, pill background) tuple.
    """
    if root in _CAT:
        return _CAT[root]
    return (root, *_UNKNOWN)


def _groups(labels: list[str]) -> dict[tuple[str, str], list[list[str]]]:
    """Group label paths by (category, provider).

    Args:
        labels: Full hierarchy paths, segments separated by '>'.

    Returns:
        A mapping of (category, provider) to the detail-segment lists
        (the segments after the provider).
    """
    g: dict[tuple[str, str], list[list[str]]] = {}
    for path in labels:
        segs = [s.strip() for s in path.split(">") if s.strip()]
        if not segs:
            continue
        cat = segs[0]
        prov = segs[1] if len(segs) > 1 else segs[0]
        g.setdefault((cat, prov), []).append(segs[2:])
    return g


def _build_trie(seglists: list[list[str]]) -> dict[str, Any]:
    """Merge segment lists into a nested dict trie (shared prefixes collapse).

    Args:
        seglists: Lists of path segments.

    Returns:
        The nested trie; leaves are empty dicts.
    """
    root: dict[str, Any] = {}
    for segs in seglists:
        node = root
        for s in segs:
            node = node.setdefault(s, {})
    return root


def _tree_html(sub: dict[str, Any]) -> str:
    """Render the label trie: one node per segment, full depth.

    Colours inherit the panel theme; leaves full, branches dimmed via opacity.

    Args:
        sub: The (sub)trie to render.

    Returns:
        The tree HTML.
    """
    out = ""
    for name, child in sub.items():
        is_leaf = not child
        marker = "·" if is_leaf else "▸"
        name_style = "" if is_leaf else "opacity:.6;"   # branch nodes dimmed
        out += (f'<div style="padding:1px 0;overflow-wrap:anywhere;">'
                f'<span style="opacity:.45">{marker} </span>'
                f'<span style="{name_style}">{html.escape(name)}</span></div>')
        if child:
            out += (f'<div style="margin-left:4px;padding-left:9px;'
                    f'border-left:1px solid {GUIDE_LINE};">{_tree_html(child)}</div>')
    return out


def _insight_html(record: dict[str, Any]) -> str:
    """Build the Common Business Services insight-card HTML for a CBS record.

    Args:
        record: The CBS lookup record (labels, ip, flows).

    Returns:
        The insight-card HTML.
    """
    labels = record.get("labels") or []
    if isinstance(labels, str):
        labels = [part for part in labels.split("\n") if part]
    g = _groups(labels)
    order = {"Cloud Providers": 0, "Content Delivery Networks (CDNs)": 1,
             "Software as a Service (SaaS)": 2, "Internet Service Providers": 3,
             "Security Services": 4, "Web Crawlers & Bots": 5}
    keys = sorted(g, key=lambda k: (order.get(k[0], 9), k[1]))

    pills = ""
    for cat, prov in keys:
        short, _accent, bg = _cat_of(cat)
        pills += (f'<span style="display:inline-block;background:{bg};color:#fff;'
                  f'padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600;'
                  f'margin:0 4px 4px 0;">{html.escape(prov)}'
                  f'<span style="opacity:.7;font-weight:400"> · {html.escape(short)}</span></span>')
    if not pills:
        pills = ('<span style="display:inline-block;background:#455A64;color:#fff;'
                 'padding:3px 10px;border-radius:12px;font-size:12px;">Cloud / CDN / SaaS</span>')

    sections = ""
    for cat, prov in keys:
        short, accent, _bg = _cat_of(cat)
        tree = _build_trie(g[(cat, prov)])
        head = (f'<div style="margin:10px 0 1px;font-weight:700;">'
                f'<span style="color:{accent}">●</span> {html.escape(prov)}'
                f'<span style="color:{accent};font-size:11px;font-weight:600;'
                f'letter-spacing:.5px;"> &nbsp;{html.escape(short.upper())}</span></div>')
        body = (f'<div style="font-size:12px;line-height:1.5;margin-left:4px;">'
                f'{_tree_html(tree)}</div>') if tree else ""
        sections += head + body

    # footer: the alert flow (from -> to) involving this IP — from alert relations.
    # margin-top:auto pins it to the card bottom once the card fills its height (via
    # the SecOps insight-card-fix plugin / a future platform fix); inert otherwise.
    # The separator sits on the pinned wrapper (matching the TI card) so both cards'
    # rules align; the footer itself is rendered without its own rule.
    footer = flow_footer_html(record.get("ip", ""), record.get("flows") or [], separator=False)
    if footer:
        footer = (f'<div style="margin-top:auto;padding-top:8px;'
                  f'border-top:1px solid {GUIDE_LINE};">{footer}</div>')

    return (
        '<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;">'
        '<div style="margin-bottom:6px;font-size:14px;font-weight:700;">Common Business Services</div>'
        f'<div style="margin-bottom:4px;">{pills}</div>'
        f'{sections}'
        f'{footer}'
        '</div>'
    )


def _join(value: Any) -> str:
    """Pipe-join a list; pass scalars through as strings.

    Args:
        value: A list to join, or a scalar.

    Returns:
        The joined string, or '' for empty input.
    """
    if isinstance(value, list):
        return "|".join(str(x) for x in value if x not in (None, "") and str(x).strip())
    return str(value) if value not in (None, "") else ""


@output_handler
def main() -> None:
    """Classify IP entities against ELLIO Common Business Services."""
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    cfg = config_reader(siemplify)
    api_root = cfg(param_name="API Root", default_value=DEFAULT_ELLIO_API_ROOT, input_type=str)
    api_key = cfg(param_name="API Key", is_mandatory=True, input_type=str)
    verify_ssl = cfg(param_name="Verify SSL", default_value=True, input_type=bool)

    ip_csv = extract_action_param(siemplify, param_name="IP Addresses", is_mandatory=False,
                                  input_type=str, default_value="", print_value=True)
    create_insight = extract_action_param(siemplify, param_name="Create Insight",
                                          default_value=True, input_type=bool, print_value=True)

    manager = EllioManager(ellio_api_root=api_root, ellio_api_key=api_key, verify_ssl=verify_ssl)

    target_ips, entity_ips, skipped = collect_target_ips(siemplify, ip_csv)
    if skipped:
        siemplify.LOGGER.info(f"Skipped non-public/internal addresses: {', '.join(skipped)}")

    json_results: dict[str, dict[str, Any]] = {}
    enriched_entities = []
    matched, unmatched, errored, errors = [], [], [], []

    for ip in target_ips:
        try:
            record = manager.cbs_lookup(ip)
        except EllioManagerError as error:
            siemplify.LOGGER.error(f"CBS lookup failed for {ip}: {error}")
            errored.append(ip)
            errors.append(str(error))
            continue
        if not record:
            unmatched.append(ip)
            continue

        # role + flow in the alert (from -> to) — from the alert relations, not CBS
        direction, flows = relations_for(siemplify, ip)
        if direction:
            record["direction"] = direction
        if flows:
            record["flows"] = flows

        json_results[ip] = record
        matched.append(ip)
        entity = entity_ips.get(ip)
        if entity is not None:
            props = {
                f"{CBS_ENRICH_PREFIX}cidr": record.get("cidr", ""),
                f"{CBS_ENRICH_PREFIX}providers": _join(record.get("providers")),
                f"{CBS_ENRICH_PREFIX}types": _join(record.get("types")),
                f"{CBS_ENRICH_PREFIX}services": _join(record.get("services")),
                f"{CBS_ENRICH_PREFIX}regions": _join(record.get("regions")),
                f"{CBS_ENRICH_PREFIX}ids": _join(record.get("cbs_ids")),
                f"{CBS_ENRICH_PREFIX}direction": direction,
            }
            entity.additional_properties.update({k: v for k, v in props.items() if v})
            entity.is_enriched = True
            if create_insight:
                siemplify.add_entity_insight(entity, _insight_html(record))
            enriched_entities.append(entity)

    if enriched_entities:
        siemplify.update_entities(enriched_entities)

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))

    if matched:
        result_value = True
        output_message = f"CBS match for {len(matched)} IP(s): {', '.join(matched)}."
        if unmatched:
            output_message += f" Not in CBS: {', '.join(unmatched)}."
        if errored:
            output_message += f" Lookup errors: {', '.join(errored)}."
        status = EXECUTION_STATE_COMPLETED
    elif errored:
        # No match and the API returned errors - a connection/auth failure, not a genuine
        # "not in CBS" result. Fail so a playbook can branch on it.
        result_value = False
        output_message = f'Error executing action "{SCRIPT_NAME}". Reason: {errors[0]}'
        status = EXECUTION_STATE_FAILED
    else:
        result_value = False
        output_message = "No IP addresses matched ELLIO Common Business Services."
        status = EXECUTION_STATE_COMPLETED

    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    siemplify.end(output_message, result_value, status)


if __name__ == "__main__":
    main()
