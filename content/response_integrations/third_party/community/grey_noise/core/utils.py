from __future__ import annotations
import re

from soar_sdk.SiemplifyDataModel import EntityTypes
from .constants import INTEGRATION_NAME, INVALID_CVE_FORMAT_ERROR
from .greynoise_exceptions import InvalidIntegerException, InvalidGranularityException


def get_integration_params(siemplify):
    """
    Retrieve the integration parameters from Siemplify configuration.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction instance

    Returns:
        str: API key for GreyNoise
    """
    api_key = siemplify.extract_configuration_param(
        INTEGRATION_NAME,
        "GN API Key",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    return api_key


def validate_integer_param(value, param_name, zero_allowed=False, allow_negative=False):
    """
    Validates if the given value is an integer and meets the requirements.

    Args:
        value (int|str): The value to be validated.
        param_name (str): The name of the parameter for error messages.
        zero_allowed (bool, optional): If True, zero is a valid integer.
            Defaults to False.
        allow_negative (bool, optional): If True, negative integers
            are allowed. Defaults to False.

    Raises:
        InvalidIntegerException: If the value is not a valid integer or
            does not meet the rules.

    Returns:
        int: The validated integer value.
    """
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise InvalidIntegerException(f"{param_name} must be an integer.")
    if not allow_negative and int_value < 0:
        raise InvalidIntegerException(f"{param_name} must be a non-negative integer.")
    if not zero_allowed and int_value == 0:
        raise InvalidIntegerException(f"{param_name} must be greater than zero.")
    return int_value


def get_cve_entities(siemplify):
    """
    Get CVE type entities from Siemplify.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction instance

    Returns:
        list: List of CVE entities
    """
    return [entity for entity in siemplify.target_entities if entity.entity_type == EntityTypes.CVE]


def validate_cve_format(cve_id):
    """
    Validate CVE ID format (CVE-YYYY-NNNN).

    Args:
        cve_id (str): CVE identifier to validate

    Returns:
        bool: True if valid format

    Raises:
        ValueError: If CVE format is invalid
    """
    pattern = r"^CVE-\d{4}-\d{4,}$"
    if not re.match(pattern, cve_id):
        raise ValueError(INVALID_CVE_FORMAT_ERROR.format(cve_id))
    return True


def get_ip_entities(siemplify):
    """
    Get IP type entities from Siemplify.

    Args:
        siemplify (SiemplifyAction): SiemplifyAction instance

    Returns:
        list: List of IP entities
    """
    return [
        entity for entity in siemplify.target_entities if entity.entity_type == EntityTypes.ADDRESS
    ]

def generate_timeline_insight(data, ip_address):
    """
    Generate HTML insight for IP Activity Timeline - Platform Theme Compatible.
    Only uses colors where semantically necessary (badges, status indicators).

    Args:
        data (dict): Timeline data from API
        ip_address (str): The IP address

    Returns:
        str: HTML content for insight
    """
    content = ""
    metadata = data.get("metadata", {})
    activity = data.get("results", [])

    content += "<div style='padding:15px; border-radius:6px;'>"

    content += (
        "<p style='margin:0 0 10px 0; font-size:16px; "
        "font-weight:bold;'>IP Activity Timeline</p>"
    )

    if not activity and not metadata:
        content += "<p>No data available</p>"
        content += "</div>"
        return content

    if metadata:
        content += "<div style='margin-bottom:15px;'>"
        content += (
            "<p style='margin:0 0 8px 0; font-size:14px; "
            "font-weight:bold;'>Timeline Overview</p>"
        )
        content += "<div style='display:flex; gap:10px; flex-wrap:wrap;'>"
        content += (
            f"<span style='padding:4px 10px; background:rgba(52,152,219,0.15); "
            f"border-radius:4px; font-size:12px;'>"
            f"<strong>Field:</strong> {metadata.get('field', 'N/A')}</span>"
        )
        content += (
            f"<span style='padding:4px 10px; background:rgba(52,152,219,0.15); "
            f"border-radius:4px; font-size:12px;'>"
            f"<strong>First Seen:</strong> {metadata.get('first_seen', 'N/A')}</span>"
        )
        content += (
            f"<span style='padding:4px 10px; background:rgba(52,152,219,0.15); "
            f"border-radius:4px; font-size:12px;'>"
            f"<strong>Granularity:</strong> {metadata.get('granularity', 'N/A')}</span>"
        )
        content += "</div></div>"

    if activity:
        has_tag_metadata = any(
            item.get("tag_metadata") for item in activity[:10]
        )


        if has_tag_metadata:
            unique_tags = {}
            for item in activity[:10]:
                tag_meta = item.get("tag_metadata", {})
                tag_id = tag_meta.get("id", "")
                if tag_id and tag_id not in unique_tags:
                    unique_tags[tag_id] = tag_meta

            content += (
                f"<p style='margin:10px 0 8px 0; font-size:14px; "
                f"font-weight:bold;'>Activity Timeline ({len(activity[:10])} events, "
                f"{len(unique_tags)} unique tags)</p>"
            )

            tag_groups = {}
            for item in activity[:10]:
                tag_meta = item.get("tag_metadata", {})
                tag_id = tag_meta.get("id", "unknown")
                if tag_id not in tag_groups:
                    tag_groups[tag_id] = []
                tag_groups[tag_id].append(item)

            for tag_id, items in tag_groups.items():
                tag_meta = items[0].get("tag_metadata", {})
                intention = (tag_meta.get("intention") or "unknown").strip() or "unknown"
                category = (tag_meta.get("category") or "N/A").strip() or "N/A"
                name = (tag_meta.get("name") or "Unknown Tag").strip() or "Unknown Tag"
                description = (tag_meta.get("description") or "").strip()
                recommend_block = tag_meta.get("recommend_block", False)

                intention_colors = {
                    "malicious": "background:rgba(204,51,51,0.2); border-left:4px solid #c33",
                    "suspicious": "background:rgba(253,203,110,0.2); border-left:4px solid #fdcb6e",
                    "benign": "background:rgba(116,185,255,0.2); border-left:4px solid #74b9ff",
                    "unknown": "background:rgba(153,153,153,0.2); border-left:4px solid #999"
                }
                bg_style = intention_colors.get(
                    intention.lower(), intention_colors["unknown"]
                )

                content += (
                    f"<div style='margin:10px 0; padding:10px; {bg_style}; "
                    f"border-radius:4px;'>"
                )
                content += (
                    f"<div style='margin-bottom:8px;'>"
                    f"<strong style='font-size:13px;'>{name}</strong>"
                )

                intention_badge_colors = {
                    "malicious": "background:#c33; color:white",
                    "suspicious": "background:#fdcb6e; color:#333",
                    "benign": "background:#74b9ff; color:white",
                    "unknown": "background:#999; color:white"
                }
                badge_style = intention_badge_colors.get(
                    intention.lower(), intention_badge_colors["unknown"]
                )

                content += (
                    f"<span style='margin-left:8px; padding:2px 8px; {badge_style}; "
                    f"border-radius:3px; font-size:11px; font-weight:bold;'>"
                    f"{intention}</span>"
                )
                content += (
                    f"<span style='margin-left:6px; padding:2px 8px; background:rgb(0 0 0 / 13%); "
                    f"border-radius:3px; font-size:11px;'>{category}</span>"
                )

                if recommend_block:
                    content += (
                        "<span style='margin-left:6px; padding:2px 8px; background:#c33; "
                        "color:white; border-radius:3px; font-size:11px; "
                        "font-weight:bold;'>BLOCK</span>"
                    )
                content += "</div>"

                if description:
                    short_desc = description[:150] + '...' if len(description) > 150 else description
                    content += (
                        f"<p style='margin:5px 0; font-size:12px;'>{short_desc}</p>"
                    )

                content += (
                    "<table style='width:100%; margin-top:8px; font-size:12px; "
                    "border-collapse:collapse;'><tbody>"
                )
                content += (
                    "<tr style='background:rgba(128,128,128,0.1);'>"
                    f"<th style='padding:4px 8px; text-align:left; "
                    f"border-bottom:1px solid rgba(128,128,128,0.2);'>Timestamp</th>"
                    "<th style='padding:4px 8px; text-align:right; "
                    "border-bottom:1px solid rgba(128,128,128,0.2);'>Count</th></tr>"
                )

                for item in items:
                    timestamp = item.get("timestamp", "")
                    data_count = item.get("data", "")
                    content += (
                        f"<tr style='background:rgba(128,128,128,0.05);'>"
                        f"<td style='padding:4px 8px;'>{timestamp}</td>"
                        f"<td style='padding:4px 8px; text-align:right;'>"
                        f"<strong>{data_count}</strong></td></tr>"
                    )

                content += "</tbody></table></div>"

        else:
            content += (
                f"<p style='margin:10px 0 8px 0; font-size:14px; "
                f"font-weight:bold;'>Activity Timeline ({len(activity[:10])} events)</p>"
            )
            content += (
                "<table style='width:100%; border:1px solid rgba(128,128,128,0.2); "
                "border-collapse:collapse;'><tbody>"
            )
            content += (
                "<tr style='background:rgba(128,128,128,0.1);'>"
                f"<th style='padding:8px; text-align:left;'>Timestamp</th>"
                f"<th style='padding:8px; text-align:left;'>{metadata.get('field', 'Label')}</th>"
                "<th style='padding:8px; text-align:right;'>Count</th></tr>"
            )

            for item in activity[:10]:
                timestamp = item.get("timestamp", "")
                label = item.get("label", "")
                data_count = item.get("data", "")

                content += (
                    f"<tr style='border-bottom:1px solid rgba(128,128,128,0.1);'>"
                    f"<td style='padding:8px;'>{timestamp}</td>"
                    f"<td style='padding:8px;'>{label}</td>"
                    f"<td style='padding:8px; text-align:right;'>"
                    f"<strong>{data_count}</strong></td></tr>"
                )

            content += "</tbody></table>"

        if len(activity) > 10:
            content += (
                f"<p style='margin-top:10px; font-size:12px; opacity:0.7;'>"
                f"Showing 10 of {len(activity)} events</p>"
            )
    else:
        content += "<p>No Activities found.</p>"

    content += (
        f'<p style="margin-top:15px;"><strong><a target="_blank" '
        f"href='https://viz.greynoise.io/ip/{ip_address}?view=timeline' "
        f"style='color:#3498db;'>View Full Timeline</a></strong></p>"
    )

    content += "</div>"

    return content


def generate_ip_lookup_insight(data, ip_address):
    """
    Generate HTML insight for IP Lookup - Platform Theme Compatible.
    Only uses colors where semantically necessary (badges, status indicators).

    Args:
        data (dict): IP lookup data from API
        ip_address (str): The IP address

    Returns:
        str: HTML content for insight
    """
    content = ""
    bsi = data.get("business_service_intelligence", {})
    isi = data.get("internet_scanner_intelligence", {})
    metadata = isi.get("metadata", {})
    if not isi.get("found") and not bsi.get("found"):
        content += (
            f"<div style='padding:15px; background:rgba(128,128,128,0.1); "
            f"border-left:4px solid #95a5a6; border-radius:4px;'>"
        )
        content += (
            "<p style='margin:0 0 8px 0; font-size:13px; "
            "font-weight:bold; opacity:0.7;'>Business Service</p>"
        )
        content += (
            f"<div style='font-size:24px; font-weight:bold; "
            f"color:#95a5a6; margin-bottom:8px;'>NOT FOUND</div>"
        )
        content += "</div>"
        content += (
            f"<div style='padding:15px; background:rgba(128,128,128,0.1); "
            f"border-left:4px solid #95a5a6; border-radius:4px;'>"
        )
        content += (
            "<p style='margin:0 0 8px 0; font-size:13px; "
            "font-weight:bold; opacity:0.7;'>Internet Scanner</p>"
        )

        content += (
            f"<div style='font-size:24px; font-weight:bold; "
            f"color:#95a5a6; margin-bottom:8px;'>NOT FOUND</div>"
        )
        content += "</div>"
        return content

    content += "<div style='padding:15px; border-radius:6px;'>"

    content += "<div style='margin-bottom:15px;'>"
    content += (
        "<p style='margin:0 0 8px 0; font-size:16px; "
        "font-weight:bold;'>IP Intelligence Overview</p>"
    )
    content += (
        "<div style='display:flex; gap:8px; margin-bottom:10px; "
        "flex-wrap:wrap;'>"
    )
    if isi.get("found") and isi.get('classification'):
        classification = isi['classification'] if isi and isi.get('classification') else 'unknown'
        classification_colors = {
            "malicious": "background:#c33; color:white",
            "suspicious": "background:#f39c12; color:white",
            "benign": "background:#27ae60; color:white",
            "unknown": "background:#95a5a6; color:white"
        }
        class_color = classification_colors.get(
            classification.lower(), classification_colors["unknown"]
        )
        content += (
            f"<span style='padding:4px 12px; {class_color}; "
            f"border-radius:4px; font-size:13px; font-weight:bold;'>"
            f"{classification.upper()}</span>"
        )

    if isi.get("actor") and isi.get("actor") != "unknown":
        content += (
            f"<span style='padding:4px 12px; background:#34495e; "
            f"color:white; border-radius:4px; font-size:13px;'>"
            f"{isi.get('actor')}</span>"
        )

    if bsi.get("found"):
        content += (
            "<span style='padding:4px 12px; background:#3498db; "
            "color:white; border-radius:4px; font-size:13px; "
            "font-weight:bold;'>BUSINESS SERVICE</span>"
        )

    content += "</div>"

    # Info grid
    content += (
        "<div style='display:grid; grid-template-columns: "
        "repeat(auto-fit, minmax(180px, 1fr)); gap:10px; "
        "margin-bottom:10px;'>"
    )

    if isi.get("first_seen"):
        content += (
            "<div style='padding:8px; background:rgba(128,128,128,0.1); "
            "border-radius:4px;'>"
            "<div style='font-size:11px; opacity:0.7;'>First Seen</div>"
            f"<div style='font-size:13px; font-weight:bold;'>"
            f"{isi.get('first_seen')}</div></div>"
        )

    if isi.get("last_seen"):
        content += (
            "<div style='padding:8px; background:rgba(128,128,128,0.1); "
            "border-radius:4px;'>"
            "<div style='font-size:11px; opacity:0.7;'>Last Seen</div>"
            f"<div style='font-size:13px; font-weight:bold;'>"
            f"{isi.get('last_seen')}</div></div>"
        )

    if metadata.get("source_country"):
        content += (
            "<div style='padding:8px; background:rgba(128,128,128,0.1); "
            "border-radius:4px;'>"
            "<div style='font-size:11px; opacity:0.7;'>Country</div>"
            f"<div style='font-size:13px; font-weight:bold;'>"
            f"{metadata.get('source_country')}</div></div>"
        )

    if metadata.get("organization"):
        content += (
            "<div style='padding:8px; background:rgba(128,128,128,0.1); "
            "border-radius:4px;'>"
            "<div style='font-size:11px; opacity:0.7;'>Organization</div>"
            f"<div style='font-size:13px; font-weight:bold;'>"
            f"{metadata.get('organization')}</div></div>"
        )

    content += "</div>"

    # Bot/VPN/Service badges
    content += (
        "<div style='display:flex; gap:10px; margin-bottom:10px; "
        "flex-wrap:wrap;'>"
    )
    if isi.get('bot'):
        bot_color = "#e74c3c" if isi.get('bot') else "#95a5a6"
        content += (
            f"<div style='padding:6px 12px; background:{bot_color}; "
            f"color:white; border-radius:4px; font-size:12px;'>"
            f"<strong>Bot:</strong> {isi.get('bot', False)}</div>"
        )

    if isi.get('vpn'):
        vpn_color = "#e67e22" if isi.get('vpn') else "#95a5a6"
        content += (
            f"<div style='padding:6px 12px; background:{vpn_color}; "
            f"color:white; border-radius:4px; font-size:12px;'>"
            f"<strong>VPN:</strong> {isi.get('vpn', False)}</div>"
        )

    if bsi.get("found") and bsi.get("name"):
        content += (
            "<div style='padding:6px 12px; background:#3498db; "
            "color:white; border-radius:4px; font-size:12px;'>"
            f"<strong>Service:</strong> {bsi.get('name')}</div>"
        )

    content += "</div></div>"

    # Tags with color coding
    tags = isi.get("tags", [])
    if tags:
        content += "<div style='margin-bottom:15px;'>"
        content += (
            "<p style='margin:0 0 8px 0; font-size:14px; "
            "font-weight:bold;'>Tags (Top 5)</p>"
        )
        content += "<div style='display:flex; flex-wrap:wrap; gap:6px;'>"

        for tag in tags[:5]:
            intention = tag["intention"] if tag.get("intention") else "unknown"
            intention_colors = {
                "malicious": "background:rgba(204,51,51,0.2); border:1px solid #c33; color:#ff6b6b",
                "suspicious": "background:rgba(253,203,110,0.2); border:1px solid #fdcb6e; color:#ffd93d",
                "benign": "background:rgba(39,174,96,0.2); border:1px solid #27ae60; color:#6bcf7f",
                "unknown": "background:rgba(149,165,166,0.2); border:1px solid #95a5a6"
            }
            tag_color = intention_colors.get(
                intention.lower(), intention_colors["unknown"]
            )

            content += (
                f"<div style='padding:6px 10px; {tag_color}; "
                f"border-radius:4px; font-size:12px;'>"
                f"<strong>{tag.get('name', '')}</strong>"
            )
            if tag.get("category"):
                content += (
                    f" <span style='opacity:0.7;'>({tag.get('category')})</span>"
                )
            content += "</div>"

        content += "</div></div>"

    # CVEs with alert styling
    cves = isi.get("cves", [])
    if cves:
        content += (
            "<div style='margin-bottom:15px; padding:10px; "
            "background:rgba(255,193,7,0.2); border-left:4px solid #ffc107; "
            "border-radius:4px;'>"
            "<p style='margin:0 0 5px 0; font-size:13px; "
            "font-weight:bold;'>Associated CVEs</p>"
            f"<p style='margin:0; font-size:12px;'>{', '.join(cves[:5])}</p>"
            "</div>"
        )

    content += (
        f'<p style="margin-top:15px;"><strong>More Info: <a target="_blank" '
        f"href='https://viz.greynoise.io/ip/{ip_address}' "
        f"style='color:#3498db;'>View Full IP Details</a></strong></p>"
    )

    content += "</div>"

    return content


def generate_cve_insight(data, cve_id):
    """
    Generate HTML insight for CVE Lookup - Platform Theme Compatible.
    Only uses colors where semantically necessary (badges, status indicators).

    Args:
        data (dict): CVE lookup data from API
        cve_id (str): The CVE identifier

    Returns:
        str: HTML content for insight
    """
    content = ""
    details = data.get("details", {})
    timeline = data.get("timeline", {})
    exploitation_details = data.get("exploitation_details", {})
    exploitation_stats = data.get("exploitation_stats", {})
    exploitation_activity = data.get("exploitation_activity", {})

    cvss_score = details.get('cve_cvss_score', 0)
    if cvss_score >= 9.0:
        severity_color = "background:#c33; color:white"
    elif cvss_score >= 7.0:
        severity_color = "background:#e74c3c; color:white"
    elif cvss_score >= 4.0:
        severity_color = "background:#f39c12; color:white"
    elif cvss_score > 0:
        severity_color = "background:#3498db; color:white"
    else:
        severity_color = "background:#95a5a6; color:white"

    content += "<div style='padding:15px; border-radius:6px;'>"

    # Threat Assessment Header
    content += "<div style='margin-bottom:12px;'>"
    content += (
        "<p style='margin:0 0 8px 0; font-size:14px; "
        "font-weight:bold;'>Threat Assessment</p>"
    )
    content += "<div style='display:flex; gap:6px; margin-bottom:8px; flex-wrap:wrap;'>"
    content += (
        f"<span style='padding:5px 12px; {severity_color}; "
        f"border-radius:4px; font-size:12px; font-weight:bold;'>"
        f"CVSS {cvss_score}</span>"
    )
    if exploitation_details.get('exploitation_registered_in_kev'):
        content += (
            "<span style='padding:5px 12px; background:#e74c3c; "
            "color:white; border-radius:4px; font-size:12px; "
            "font-weight:bold;'>🚨 CISA KEV</span>"
        )
    if exploitation_details.get('exploit_found'):
        content += (
            "<span style='padding:5px 12px; background:#e67e22; "
            "color:white; border-radius:4px; font-size:12px; "
            "font-weight:bold;'>EXPLOIT AVAILABLE</span>"
        )
    content += "</div>"

    if details.get("vulnerability_name"):
        content += (
            f"<p style='margin:0 0 6px 0; font-size:13px; "
            f"font-weight:bold;'>"
            f"{details.get('vulnerability_name')}</p>"
        )

    if details.get("vulnerability_description"):
        desc = details.get('vulnerability_description')
        content += (
            f"<p style='margin:0 0 6px 0; font-size:11px; "
            f"line-height:1.4;'>{desc}</p>"
        )

    content += "<div style='display:flex; gap:8px; font-size:10px; opacity:0.7;'>"
    if details.get("vendor"):
        content += f"<span>🏢 {details.get('vendor')}</span>"
    if details.get("product"):
        content += f"<span>📦 {details.get('product')}</span>"
    content += "</div></div>"

    # Exploitation Intelligence
    content += (
        "<div style='margin-bottom:12px; padding:10px; "
        "background:rgba(128,128,128,0.1); border-radius:4px;'>"
    )
    content += (
        "<p style='margin:0 0 8px 0; font-size:13px; "
        "font-weight:bold;'>Exploitation Intelligence</p>"
    )
    content += (
        "<div style='display:grid; grid-template-columns: repeat(2, 1fr); "
        "gap:8px;'>"
    )

    exploit_found = exploitation_details.get('exploit_found', False)
    exploit_color = "#e74c3c" if exploit_found else "#27ae60"
    content += (
        f"<div style='padding:8px; background:rgba(128,128,128,0.05); "
        f"border-left:3px solid {exploit_color}; border-radius:3px;'>"
        f"<div style='font-size:10px; opacity:0.7;'>Exploit Found</div>"
        f"<div style='font-size:13px; font-weight:bold; "
        f"color:{exploit_color};'>{'YES' if exploit_found else 'NO'}</div></div>"
    )

    epss_score = exploitation_details.get('epss_score', 0)
    epss_color = (
        "#e74c3c" if epss_score > 0.5 else
        "#f39c12" if epss_score > 0.2 else "#27ae60"
    )
    content += (
        f"<div style='padding:8px; background:rgba(128,128,128,0.05); "
        f"border-left:3px solid {epss_color}; border-radius:3px;'>"
        f"<div style='font-size:10px; opacity:0.7;'>EPSS Score</div>"
        f"<div style='font-size:13px; font-weight:bold; "
        f"color:{epss_color};'>{epss_score}</div></div>"
    )

    if exploitation_details.get("attack_vector"):
        content += (
            f"<div style='padding:8px; background:rgba(128,128,128,0.05); "
            f"border-left:3px solid #3498db; border-radius:3px;'>"
            f"<div style='font-size:10px; opacity:0.7;'>Attack Vector</div>"
            f"<div style='font-size:13px; font-weight:bold;'>"
            f"{exploitation_details.get('attack_vector')}</div></div>"
        )

    num_exploits = exploitation_stats.get('number_of_available_exploits', 0)
    content += (
        f"<div style='padding:8px; background:rgba(128,128,128,0.05); "
        f"border-left:3px solid #95a5a6; border-radius:3px;'>"
        f"<div style='font-size:10px; opacity:0.7;'>Available Exploits</div>"
        f"<div style='font-size:13px; font-weight:bold;'>{num_exploits}</div></div>"
    )

    content += "</div>"

    num_actors = exploitation_stats.get(
        'number_of_threat_actors_exploiting_vulnerability', 0
    )
    num_botnets = exploitation_stats.get(
        'number_of_botnets_exploiting_vulnerability', 0
    )
    if num_actors > 0 or num_botnets > 0:
        content += (
            "<div style='margin-top:8px; padding:6px; "
            "background:rgba(255,193,7,0.2); "
            "border-radius:3px; font-size:11px;'>"
            f"<strong>⚠️ Threat Activity:</strong> {num_actors} actors, "
            f"{num_botnets} botnets</div>"
        )
    content += "</div>"

    # Active Exploitation Activity
    if exploitation_activity and exploitation_activity.get('activity_seen'):
        threat_1d = exploitation_activity.get('threat_ip_count_1d', 0)
        threat_30d = exploitation_activity.get('threat_ip_count_30d', 0)

        content += (
            "<div style='margin-bottom:12px; padding:10px; "
            "background:rgba(231,76,60,0.15); "
            "border-left:4px solid #e74c3c; border-radius:4px;'>"
        )
        content += (
            "<p style='margin:0 0 6px 0; font-size:12px; "
            "font-weight:bold; color:#c33;'>"
            "🚨 Active Exploitation Detected</p>"
        )
        content += (
            "<div style='display:flex; gap:15px; font-size:11px;'>"
            f"<div><strong style='color:#e74c3c;'>{threat_1d}</strong> "
            "<span style='opacity:0.7;'>threat IPs (24h)</span></div>"
            f"<div><strong style='color:#e74c3c;'>{threat_30d}</strong> "
            "<span style='opacity:0.7;'>threat IPs (30d)</span></div>"
            "</div></div>"
        )

    # Timeline (compact)
    if timeline.get("cve_published_date") or timeline.get("cisa_kev_date_added"):
        content += (
            "<div style='padding:8px; background:rgba(128,128,128,0.1); "
            "border-radius:3px; font-size:10px; opacity:0.8;'>"
        )
        if timeline.get("cve_published_date"):
            pub_date = timeline.get("cve_published_date", "").split("T")[0]
            content += f"📅 Published: {pub_date}"
        if timeline.get("cisa_kev_date_added"):
            if timeline.get("cve_published_date"):
                content += " | "
            content += (
                f"<span style='color:#e74c3c; font-weight:bold;'>"
                f"KEV Added: {timeline.get('cisa_kev_date_added')}</span>"
            )
        content += "</div>"

    content += (
        f"<p style='margin-top:12px; font-size:11px;'>"
        f"<strong><a target='_blank' "
        f"href='https://viz.greynoise.io/cves/{cve_id}' "
        f"style='color:#3498db;'>"
        f"View Full CVE Details →</a></strong></p>"
    )

    content += "</div>"

    return content

def generate_quick_ip_insight(data, ip_address):
    """
    Generate HTML insight for Quick IP Lookup - Platform Theme Compatible.
    Only uses colors where semantically necessary (badges, status indicators).

    Args:
        data (dict): Quick IP lookup data from API
        ip_address (str): The IP address

    Returns:
        str: HTML content for insight
    """
    content = ""
    bsi = data.get("business_service_intelligence", {})
    isi = data.get("internet_scanner_intelligence", {})

    content += "<div style='padding:15px; border-radius:6px;'>"

    content += "<div style='margin-bottom:15px;'>"
    content += (
        "<p style='margin:0 0 12px 0; font-size:16px; "
        "font-weight:bold;'>Quick IP Intelligence</p>"
    )

    content += (
        "<div style='display:grid; grid-template-columns: 1fr 1fr; "
        "gap:15px;'>"
    )

    # Business Service Intelligence Card
    bsi_color = "#27ae60" if bsi.get('found') else "#95a5a6"
    content += (
        f"<div style='padding:15px; background:rgba(128,128,128,0.1); "
        f"border-left:4px solid {bsi_color}; border-radius:4px;'>"
    )
    content += (
        "<p style='margin:0 0 8px 0; font-size:13px; "
        "font-weight:bold; opacity:0.7;'>Business Service</p>"
    )
    bsi_status = "FOUND" if bsi.get('found') else "NOT FOUND"
    content += (
        f"<div style='font-size:24px; font-weight:bold; "
        f"color:{bsi_color}; margin-bottom:8px;'>{bsi_status}</div>"
    )

    if bsi.get("trust_level"):
        content += (
            "<div style='padding:4px 8px; background:rgba(128,128,128,0.15); "
            "border-radius:3px; display:inline-block; font-size:12px;'>"
            f"<strong>Trust Level:</strong> {bsi.get('trust_level')}</div>"
        )

    content += "</div>"

    # Internet Scanner Intelligence Card
    classification = isi.get("classification", "unknown")
    classification_colors = {
        "malicious": "#c33",
        "suspicious": "#f39c12",
        "benign": "#27ae60",
        "unknown": "#95a5a6"
    }
    isi_color = classification_colors.get(
        classification.lower(), classification_colors["unknown"]
    )

    content += (
        f"<div style='padding:15px; background:rgba(128,128,128,0.1); "
        f"border-left:4px solid {isi_color}; border-radius:4px;'>"
    )
    content += (
        "<p style='margin:0 0 8px 0; font-size:13px; "
        "font-weight:bold; opacity:0.7;'>Internet Scanner</p>"
    )
    isi_status = "FOUND" if isi.get('found') else "NOT FOUND"
    content += (
        f"<div style='font-size:24px; font-weight:bold; "
        f"color:{isi_color}; margin-bottom:8px;'>{isi_status}</div>"
    )

    if isi.get("classification"):
        content += (
            f"<div style='padding:4px 8px; background:{isi_color}; "
            f"color:white; border-radius:3px; display:inline-block; "
            f"font-size:12px; font-weight:bold;'>"
            f"{classification.upper()}</div>"
        )

    content += "</div>"
    content += "</div></div>"

    content += (
        f"<p style='margin-top:15px;'><strong>More Info: "
        f"<a target='_blank' "
        f"href='https://viz.greynoise.io/ip/{ip_address}' "
        f"style='color:#3498db;'>"
        f"View Full IP Details</a></strong></p>"
    )

    content += "</div>"

    return content


