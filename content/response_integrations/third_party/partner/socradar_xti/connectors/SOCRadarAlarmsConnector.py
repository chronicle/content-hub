"""
SOCRadar Alarms Connector
=========================
Chronicle SOAR native connector. Ingests SOCRadar alarms as alerts.
Uses SOAR SDK (SiemplifyConnectorExecution, AlertInfo).
"""
from __future__ import annotations
from typing import Any

import ipaddress
import re
import sys
import json
import time
from datetime import datetime, timezone

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from ..core.SOCRadarManager import SOCRadarManager, SOCRadarManagerError

CONNECTOR_NAME = "SOCRadar Alarms Connector"
VENDOR = "SOCRadar"
PRODUCT = "SOCRadar CTI"
DEFAULT_DAYS_BACKWARDS = 1
DEFAULT_MAX_ALERTS = 100
# Alarm severity → SOAR risk score (midpoint of each band)
# CRITICAL: 80-100 → 90, HIGH: 60-79 → 70, MEDIUM: 40-59 → 50, LOW: 20-39 → 30, INFO: 0-19 → 10
RISK_SCORE_MAP = {"CRITICAL": 90, "HIGH": 70, "MEDIUM": 50, "LOW": 30, "INFO": 10}



# --- Indicator extraction patterns ---
IP_PATTERN = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b")
URL_PATTERN = re.compile(r"https?://[^\s\'\"<>]+", re.IGNORECASE)
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
HASH_MD5 = re.compile(r"\b[a-fA-F0-9]{32}\b")
HASH_SHA1 = re.compile(r"\b[a-fA-F0-9]{40}\b")
HASH_SHA256 = re.compile(r"\b[a-fA-F0-9]{64}\b")
MAX_INDICATORS_PER_TYPE = 50


def _split_csv(val: str | list | None) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        items = val
    else:
        items = re.split(r"[,;\s]+", str(val))
    return [str(i).strip() for i in items if str(i).strip()]


def _is_public_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False



def _safe_str(val: str | list | None) -> str:
    """Extract a string value from a field that may be a string or list."""
    if isinstance(val, list):
        return str(val[0]).strip() if val else ""
    return str(val).strip() if val else ""

def _extract_indicators(alarm: dict[str, Any]) -> dict[str, list[str]]:
    """Extract IOCs from alarm content and alarm_text. Returns dict of sorted unique lists."""
    content = alarm.get("content") if isinstance(alarm, dict) else None
    if not isinstance(content, dict):
        content = {}
    text = str(alarm.get("alarm_text", "") or "")

    ips, domains, urls, emails, hashes = set(), set(), set(), set(), set()

    # From structured content fields (typically comma-separated strings)
    for ip in _split_csv(content.get("compromised_ips")):
        ips.add(ip)
    if content.get("ip_address"):
        for ip in _split_csv(content.get("ip_address")):
            ips.add(ip)
    for d in _split_csv(content.get("compromised_domains")):
        domains.add(d.lower())
    if content.get("domain"):
        for d in _split_csv(content.get("domain")):
            domains.add(d.lower())
    for e in _split_csv(content.get("compromised_emails")):
        emails.add(e.lower())
    if content.get("email"):
        for e in _split_csv(_safe_str(content.get("email"))):
            emails.add(e.lower())
    if content.get("url"):
        val = _safe_str(content.get("url"))
        if val:
            urls.add(val)
    if content.get("log_content_link"):
        val = _safe_str(content.get("log_content_link"))
        if val:
            urls.add(val)
    if content.get("hash_value"):
        for h in _split_csv(content.get("hash_value")):
            hashes.add(h.lower())

    # From credential_details (each may have URL field)
    creds_iter = content.get("credential_details") or []
    if not isinstance(creds_iter, list):
        creds_iter = []
    for cred in creds_iter:
        if isinstance(cred, dict):
            if cred.get("URL"):
                urls.add(str(cred["URL"]).strip())
            if cred.get("User") and "@" in str(cred["User"]):
                emails.add(str(cred["User"]).strip().lower())

    # Regex scan over alarm_text for free-form IOCs
    if text:
        urls.update(URL_PATTERN.findall(text))
        emails.update(m.lower() for m in EMAIL_PATTERN.findall(text))
        for ip in IP_PATTERN.findall(text):
            ips.add(ip)
        hashes.update(m.lower() for m in HASH_SHA256.findall(text))
        hashes.update(m.lower() for m in HASH_SHA1.findall(text))
        hashes.update(m.lower() for m in HASH_MD5.findall(text))

    # Filter
    ips = {ip for ip in ips if _is_public_ip(ip)}
    urls = {u for u in urls if u.startswith(("http://", "https://"))}
    domains = {d for d in domains if "." in d and 3 < len(d) <= 253
              and not d.replace(".", "").isdigit()  # exclude IPs
              and "@" not in d  # exclude emails
              and "/" not in d}  # exclude URLs/paths

    return {
        "ips": sorted(ips)[:MAX_INDICATORS_PER_TYPE],
        "domains": sorted(domains)[:MAX_INDICATORS_PER_TYPE],
        "urls": sorted(urls)[:MAX_INDICATORS_PER_TYPE],
        "emails": sorted(emails)[:MAX_INDICATORS_PER_TYPE],
        "hashes": sorted(hashes)[:MAX_INDICATORS_PER_TYPE],
    }


def _indicators_to_events(alarm: dict[str, Any], base_event: dict[str, Any]) -> tuple[list[dict], dict]:
    """Create one event per indicator with Siemplify entity-recognized field names.
    These get picked up by the Ontology resolver and become Entities on the case."""
    indicators = _extract_indicators(alarm)
    base_id = base_event.get("alarm_id", "")
    events = []

    event_time_ms = base_event.get("StartTime", str(unix_now()))

    common_fields = {
        "alarm_id": base_id,
        "device_vendor": VENDOR,
        "device_product": PRODUCT,
        "event_type": "indicator",
        "DeviceVendor": VENDOR,
        "DeviceProduct": PRODUCT,
        "SourceType": "SOCRadar Indicator",
        "EventType": "indicator",
        "StartTime": event_time_ms,
        "EndTime": event_time_ms,
        "managerReceiptTime": event_time_ms,
    }

    for ip in indicators["ips"]:
        events.append({**common_fields,
                       "Name": f"IP: {ip}",
                       "indicator_type": "IP_ADDRESS",
                       "indicator_value": ip,
                       "device_ip": ip,
                       "source_ip": ip})
    for domain in indicators["domains"]:
        events.append({**common_fields,
                       "Name": f"Domain: {domain}",
                       "indicator_type": "DOMAIN",
                       "indicator_value": domain,
                       "domain": domain,
                       "dest_host_name": domain})
    for url in indicators["urls"]:
        events.append({**common_fields,
                       "Name": f"URL: {url[:80]}",
                       "indicator_type": "URL",
                       "indicator_value": url,
                       "url": url,
                       "request_url": url})
    for email in indicators["emails"]:
        events.append({**common_fields,
                       "Name": f"Email: {email}",
                       "indicator_type": "EMAIL",
                       "indicator_value": email,
                       "email_address": email,
                       "src_user": email})
    for h in indicators["hashes"]:
        events.append({**common_fields,
                       "Name": f"Hash: {h[:32]}...",
                       "indicator_type": "FILE_HASH",
                       "indicator_value": h,
                       "file_hash": h})

    return events, indicators


def build_alert(siemplify: SiemplifyConnectorExecution, alarm: dict[str, Any], company_id: str = "", extract_indicators: bool = True) -> AlertInfo:
    alarm_id = str(alarm.get("alarm_id", ""))
    atd = alarm.get("alarm_type_details") or {}
    if not isinstance(atd, dict):
        atd = {}
    severity = (alarm.get("alarm_risk_level") or "MEDIUM").upper()
    content = alarm.get("content") or {}
    if not isinstance(content, dict):
        content = {}

    alert_info = AlertInfo()
    alert_info.display_id = alarm_id
    alert_info.ticket_id = alarm_id
    title = atd.get("alarm_generic_title", "") or (alarm.get("alarm_text", "") or "")[:120]
    alert_info.name = f"[#{alarm_id}] {title}" if alarm_id else title
    desc = alarm.get("alarm_text", "") or ""
    if len(desc) > 5000:
        desc = desc[:5000] + "...[truncated, see alarm_text field for full content]"
    alert_info.description = desc
    alert_info.device_vendor = VENDOR
    alert_info.device_product = PRODUCT
    alert_info.rule_generator = atd.get("alarm_sub_type", "SOCRadar Alarm")
    alert_info.priority = int(RISK_SCORE_MAP.get(severity, 50))
    # severity (string) is consumed by Chronicle UI for the Severity badge in Alert Details
    alert_info.severity = severity
    alert_info.start_time = _parse_date(alarm.get("date"))
    alert_info.end_time = _parse_date(alarm.get("date"))
    base_event = _flatten_alarm(alarm)
    # Environment routing from connector params
    env_field = siemplify.extract_connector_param("Environment Field Name", default_value="")
    env_regex = siemplify.extract_connector_param("Environment Regex Pattern", default_value=".*")
    if env_field and base_event.get(env_field):
        env_val = str(base_event[env_field])
        try:
            match = re.search(env_regex, env_val)
        except re.error:
            match = None
        alert_info.environment = match.group(0) if match else siemplify.context.connector_info.environment
    else:
        alert_info.environment = siemplify.context.connector_info.environment
    if company_id:
        base_event["company_id"] = str(company_id)

    if extract_indicators:
        indicator_events, indicators = _indicators_to_events(alarm, base_event)
        base_event["indicators_ips"] = json.dumps(indicators["ips"])
        base_event["indicators_domains"] = json.dumps(indicators["domains"])
        base_event["indicators_urls"] = json.dumps(indicators["urls"])
        base_event["indicators_emails"] = json.dumps(indicators["emails"])
        base_event["indicators_hashes"] = json.dumps(indicators["hashes"])
        base_event["indicators_count"] = str(
            len(indicators["ips"]) + len(indicators["domains"]) +
            len(indicators["urls"]) + len(indicators["emails"]) + len(indicators["hashes"])
        )
        alert_info.events = [base_event] + indicator_events
    else:
        alert_info.events = [base_event]
    return alert_info


def _parse_date(date_str: str | None) -> int:
    if not date_str:
        return unix_now()
    try:
        dt = datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
        return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
    except (ValueError, TypeError):
        return unix_now()




def _parse_date_safe(date_str: str | None) -> int:
    """Parse date string to ms timestamp. Returns 0 on failure (safe for checkpoint comparison)."""
    if not date_str:
        return 0
    try:
        dt = datetime.strptime(str(date_str), "%Y-%m-%d %H:%M:%S")
        return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
    except (ValueError, TypeError):
        return 0

def _flatten_alarm(alarm: dict[str, Any]) -> dict[str, Any]:
    atd = alarm.get("alarm_type_details") or {}
    if not isinstance(atd, dict):
        atd = {}
    content = alarm.get("content") or {}
    severity = (alarm.get("alarm_risk_level") or "MEDIUM").upper()

    # Compute timestamps once — SOAR expects millisecond unix timestamps
    event_time_ms = _parse_date(alarm.get("date"))
    last_notif_ms = _parse_date(alarm.get("last_notification_date")) or event_time_ms
    title = str(atd.get("alarm_generic_title", "")) or str(alarm.get("alarm_text", ""))[:120]
    desc = str(alarm.get("alarm_text", ""))
    response = str(alarm.get("alarm_response", ""))
    mitigation = str(atd.get("alarm_default_mitigation_plan", ""))
    detection = str(atd.get("alarm_detection_and_analysis", ""))

    event = {
        # --- Raw SOCRadar fields ---
        "alarm_id": str(alarm.get("alarm_id", "")),
        "alarm_text": desc,
        "alarm_risk_level": str(alarm.get("alarm_risk_level", "")),
        "alarm_asset": str(alarm.get("alarm_asset", "")),
        "alarm_response": response,
        "status": str(alarm.get("status", "")),
        "date": str(alarm.get("date", "")),
        "notification_id": str(alarm.get("notification_id", "")),
        "alarm_generic_title": str(atd.get("alarm_generic_title", "")),
        "alarm_main_type": str(atd.get("alarm_main_type", "")),
        "alarm_sub_type": str(atd.get("alarm_sub_type", "")),
        "alarm_default_risk_level": str(atd.get("alarm_default_risk_level", "")),
        "alarm_default_mitigation_plan": mitigation,
        "alarm_detection_and_analysis": detection,
        "tags": json.dumps(alarm.get("tags", [])),
        "alarm_assignees": json.dumps(alarm.get("alarm_assignees", [])),
        "alarm_related_assets": json.dumps(alarm.get("alarm_related_assets", [])),
        "alarm_related_entities": json.dumps(alarm.get("alarm_related_entities", [])),
        "alarm_compliance_list": json.dumps(atd.get("alarm_compliance_list", [])),
        "is_approved": str(alarm.get("is_approved", False)),
        "risk_score": str(RISK_SCORE_MAP.get(severity, 50)),
        "device_vendor": VENDOR,
        "device_product": PRODUCT,
        # --- Chronicle SOAR UI fields (PascalCase) ---
        # These populate the Overview tab and event columns
        "Name": title,
        "Description": desc[:2000] if desc else "",
        "SourceType": "SOCRadar Alarm",
        "DeviceVendor": VENDOR,
        "DeviceProduct": PRODUCT,
        "EventType": str(atd.get("alarm_sub_type", "SOCRadar Alarm")),
        "CategoryOutcome": str(atd.get("alarm_main_type", "")),
        "Severity": severity,
        "Priority": str(RISK_SCORE_MAP.get(severity, 50)),
        "RuleGenerator": str(atd.get("alarm_sub_type", "SOCRadar Alarm")),
        # Timestamps as millisecond unix — SOAR requires this format
        "StartTime": str(event_time_ms),
        "EndTime": str(last_notif_ms),
        "managerReceiptTime": str(event_time_ms),
        # --- Overview enrichment fields ---
        "AffectedAsset": str(alarm.get("alarm_asset", "")),
        "RecommendedResponse": response[:2000] if response else "",
        "MitigationPlan": mitigation[:2000] if mitigation else "",
        "DetectionGuidance": detection[:2000] if detection else "",
        "SOCRadarAlarmURL": f"https://platform.socradar.com/app/alarm-management/alarm-detail/{alarm.get('alarm_id', '')}",
    }

    if isinstance(content, dict) and content:
        # Full content as JSON for fields we don't explicitly map
        try:
            pruned = {}
            for k, v in content.items():
                s = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else str(v)
                pruned[k] = v if len(s) <= 2000 else str(v)[:2000] + "...[truncated]"
            content_json = json.dumps(pruned, ensure_ascii=False)
            if len(content_json) > 8000:
                content_json = json.dumps({k: v for k, v in list(pruned.items())[:20]}, ensure_ascii=False)
            event["content_json"] = content_json
        except (TypeError, ValueError):
            event["content_json"] = "{}"
        # Common content fields flattened individually for queryability
        for k in [
            "compromised_ips", "compromised_domains", "compromised_emails",
            "ip_address", "domain", "url", "email", "hash_value", "file_name",
            "mac_address", "country", "isp", "asn", "port", "protocol",
            "cve_id", "cvss_score", "malware_family", "malware_path", "antivirus",
            "computer_name", "username", "machine_id", "hwid", "guid",
            "uac", "timezone", "app", "log_date", "socradar_process_date",
            "log_content_link", "source_full_content",
        ]:
            if k in content and content[k]:
                val = content[k]
                event[k] = json.dumps(val) if isinstance(val, (list, dict)) else str(val)

        creds = content.get("credential_details")
        if creds and isinstance(creds, list) and len(creds) > 0:
            event["credential_details"] = json.dumps(creds)
            first_cred = creds[0]
            if isinstance(first_cred, dict):
                event["credential_url"] = str(first_cred.get("URL", ""))
                event["credential_user"] = str(first_cred.get("User", ""))

    return event


@output_handler
def main(is_test_run: bool = False) -> None:
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    alerts = []

    try:
        api_root = siemplify.extract_connector_param("API Root", default_value="https://platform.socradar.com/api")
        api_key = siemplify.extract_connector_param("API Key")
        company_id = siemplify.extract_connector_param("Company ID")
        verify_ssl = siemplify.extract_connector_param("Verify SSL", default_value=True, input_type=bool)
        try:
            max_alerts = int(siemplify.extract_connector_param("Max Alerts Per Cycle", default_value=str(DEFAULT_MAX_ALERTS)))
        except (ValueError, TypeError):
            max_alerts = DEFAULT_MAX_ALERTS

        extract_indicators = siemplify.extract_connector_param("Extract Indicators", default_value=True, input_type=bool)

        severities_str = siemplify.extract_connector_param("Severity Filter", default_value="")
        status_str = siemplify.extract_connector_param("Status Filter", default_value="OPEN")
        main_types_str = siemplify.extract_connector_param("Main Type Filter", default_value="")
        sub_types_str = siemplify.extract_connector_param("Sub Type Filter", default_value="")
        tags_str = siemplify.extract_connector_param("Tags Filter", default_value="")
        assignees_str = siemplify.extract_connector_param("Assignees Filter", default_value="")

        severities = [s.strip() for s in (severities_str or "").split(",") if s.strip()] or None
        status = status_str.strip() if status_str and status_str.strip() else None
        main_types = [s.strip() for s in (main_types_str or "").split(",") if s.strip()] or None
        sub_types = [s.strip() for s in (sub_types_str or "").split(",") if s.strip()] or None
        tags = [s.strip() for s in (tags_str or "").split(",") if s.strip()] or None
        assignees = [s.strip() for s in (assignees_str or "").split(",") if s.strip()] or None

        manager = SOCRadarManager(api_root, api_key, company_id, verify_ssl)

        # Timestamps are stored in milliseconds internally (SOAR convention).
        # SOCRadar API expects seconds, so divide by 1000 when calling.
        raw_ts = siemplify.fetch_timestamp(datetime_format=False)
        try:
            last_run = int(float(raw_ts)) if raw_ts else 0
        except (ValueError, TypeError):
            last_run = 0
        if last_run <= 0:
            last_run = (int(time.time()) - (DEFAULT_DAYS_BACKWARDS * 86400)) * 1000
            siemplify.LOGGER.info(f"No saved timestamp, defaulting to {DEFAULT_DAYS_BACKWARDS} day(s) back")
        siemplify.LOGGER.info(f"Fetching alarms since epoch (ms): {last_run}")

        alarms, total = manager.get_all_incidents(
            start_date=last_run // 1000,
            limit=max_alerts,
            severities=severities, status=status,
            alarm_main_types=main_types, alarm_sub_types=sub_types,
            tags=tags, assignees=assignees,
        )

        siemplify.LOGGER.info(f"Fetched {len(alarms)} alarms (total: {total})")

        last_processed_ts = last_run
        for alarm in alarms[:max_alerts]:
            if not isinstance(alarm, dict):
                siemplify.LOGGER.warning(f"Skipping non-dict alarm entry: {type(alarm).__name__}")
                continue
            alarm_id = str(alarm.get("alarm_id", ""))
            if not alarm_id:
                continue
            try:
                alert = build_alert(siemplify, alarm, company_id=company_id, extract_indicators=extract_indicators)
                # Track newest processed alarm timestamp only after successful build
                alarm_ts = _parse_date_safe(alarm.get("date"))
                if alarm_ts and alarm_ts > last_processed_ts:
                    last_processed_ts = alarm_ts
                if is_test_run:
                    siemplify.LOGGER.info(f"[TEST] Alert built: {alarm_id}")
                alerts.append(alert)
            except Exception as e:
                siemplify.LOGGER.error(f"Failed to build alert for {alarm_id}: {e}")
                continue

        if not is_test_run:
            # Save the newest processed alarm's timestamp (not "now") so we
            # correctly resume from where we left off even if capped by max_alerts
            if last_processed_ts > last_run:
                siemplify.save_timestamp(new_timestamp=last_processed_ts + 1)
                siemplify.LOGGER.info(f"Saved timestamp: {last_processed_ts} (last processed alarm)")
            elif total == 0:
                # No alarms found at all, safe to advance to now (in ms)
                siemplify.save_timestamp(new_timestamp=int(time.time() * 1000))
        siemplify.LOGGER.info(f"Returning {len(alerts)} alerts")

    except SOCRadarManagerError as e:
        siemplify.LOGGER.error(f"SOCRadar API error: {e}")
    except Exception as e:
        siemplify.LOGGER.error(f"Connector error: {e}")
        siemplify.LOGGER.exception(e)

    siemplify.return_package(alerts)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "True":
        main(is_test_run=True)
    else:
        main()
