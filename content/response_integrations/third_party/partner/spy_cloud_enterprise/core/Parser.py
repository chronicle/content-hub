from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

VENDOR = "SpyCloud"
PRODUCT = "SpyCloud Enterprise"


def first_present(record: dict[str, Any], keys: list[str]) -> Any | None:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return value
    return None


def parse_iso_to_unix_ms(value: Any) -> int | None:
    if not value:
        return None

    if isinstance(value, (int, float)):
        return int(value if value > 10_000_000_000 else value * 1000)

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def get_udm_metadata(udm_event: dict[str, Any]) -> dict[str, Any]:
    value = udm_event.get("metadata")
    return value if isinstance(value, dict) else {}


def get_udm_principal(udm_event: dict[str, Any]) -> dict[str, Any]:
    value = udm_event.get("principal")
    return value if isinstance(value, dict) else {}


def get_udm_target(udm_event: dict[str, Any]) -> dict[str, Any]:
    value = udm_event.get("target")
    return value if isinstance(value, dict) else {}


def get_udm_security_result(udm_event: dict[str, Any]) -> dict[str, Any]:
    value = udm_event.get("security_result")
    return value if isinstance(value, dict) else {}


def get_udm_extensions(udm_event: dict[str, Any]) -> dict[str, Any]:
    value = udm_event.get("extensions")
    return value if isinstance(value, dict) else {}


def get_udm_additional(udm_event: dict[str, Any]) -> dict[str, Any]:
    value = udm_event.get("additional")
    return value if isinstance(value, dict) else {}


def get_mapped_alert_severity(udm_event: dict[str, Any]) -> int | None:
    """
    Final SecOps/SOAR-facing severity from the converter.
    Expected values: 40, 60, 80, 100
    """
    security_result = get_udm_security_result(udm_event)
    value = security_result.get("severity")

    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def get_source_spycloud_severity(udm_event: dict[str, Any]) -> int | None:
    """
    Original SpyCloud source severity preserved in extensions.
    Expected values: 2, 5, 20, 25, 30
    """
    extensions = get_udm_extensions(udm_event)
    value = extensions.get("severity")

    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def get_udm_risk_score(udm_event: dict[str, Any]) -> int | None:
    security_result = get_udm_security_result(udm_event)
    value = security_result.get("risk_score")

    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def get_udm_criticality(udm_event: dict[str, Any]) -> str:
    security_result = get_udm_security_result(udm_event)
    value = security_result.get("criticality")
    return str(value) if value not in (None, "") else ""


def get_best_identifier_from_udm(udm_event: dict[str, Any]) -> str:
    principal = get_udm_principal(udm_event)
    target = get_udm_target(udm_event)
    extensions = get_udm_extensions(udm_event)

    principal_user = principal.get("user") if isinstance(principal.get("user"), dict) else {}

    candidates = [
        principal_user.get("email_addresses"),
        principal_user.get("userid"),
        principal.get("hostname"),
        principal.get("asset_id"),
        principal.get("ip"),
        target.get("hostname"),
        target.get("url"),
        extensions.get("email"),
        extensions.get("username"),
        extensions.get("domain"),
        extensions.get("source_id"),
        extensions.get("document_id"),
        extensions.get("log_id"),
        extensions.get("infected_machine_id"),
    ]

    for value in candidates:
        if value in (None, "", [], {}):
            continue

        if isinstance(value, list):
            first_value = next((item for item in value if item not in (None, "", [], {})), None)
            if first_value is not None:
                return str(first_value)
            continue

        return str(value)

    return "unknown"


def build_stable_alert_id_from_udm(udm_event: dict[str, Any]) -> str:
    extensions = get_udm_extensions(udm_event)

    direct_id = first_present(
        extensions,
        ["document_id", "log_id", "infected_machine_id", "record_id", "id"]
    )
    if direct_id:
        return f"spycloud:{direct_id}"

    principal = get_udm_principal(udm_event)
    target = get_udm_target(udm_event)
    security_result = get_udm_security_result(udm_event)
    metadata = get_udm_metadata(udm_event)

    principal_user = principal.get("user") if isinstance(principal.get("user"), dict) else {}

    identity = {
        "event_type": metadata.get("event_type"),
        "event_timestamp": metadata.get("event_timestamp"),
        "mapped_severity": security_result.get("severity"),
        "source_severity": extensions.get("severity"),
        "email": extensions.get("email"),
        "username": extensions.get("username"),
        "source_id": extensions.get("source_id"),
        "document_id": extensions.get("document_id"),
        "log_id": extensions.get("log_id"),
        "infected_machine_id": extensions.get("infected_machine_id"),
        "principal_userid": principal_user.get("userid"),
        "principal_email_addresses": principal_user.get("email_addresses"),
        "principal_hostname": principal.get("hostname"),
        "principal_asset_id": principal.get("asset_id"),
        "principal_ip": principal.get("ip"),
        "target_hostname": target.get("hostname"),
        "target_url": target.get("url"),
    }

    raw = json.dumps(identity, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"spycloud:{digest}"


def map_priority_from_mapped_severity(mapped_severity: Any) -> int:
    """
    The converter already normalizes severity into the SecOps-style scale.
    Reuse it directly for alert priority.
    """
    try:
        numeric = int(mapped_severity)
    except (TypeError, ValueError):
        return 60

    if numeric < 0:
        return 60
    if numeric > 100:
        return 100
    return numeric


def build_rule_generator_from_udm(udm_event: dict[str, Any]) -> str:
    source_severity = get_source_spycloud_severity(udm_event)

    if source_severity == 30:
        return "SpyCloud Session Cookie Theft"
    if source_severity == 25:
        return "SpyCloud Malware Infection"
    if source_severity == 20:
        return "SpyCloud Credential Exposure"
    if source_severity == 5:
        return "SpyCloud Informational Exposure"
    if source_severity == 2:
        return "SpyCloud Email Exposure"

    metadata = get_udm_metadata(udm_event)
    event_type = metadata.get("event_type")
    if event_type:
        return f"SpyCloud {event_type}"

    return "SpyCloud"


def build_alert_name_from_udm(udm_event: dict[str, Any]) -> str:
    source_severity = get_source_spycloud_severity(udm_event)
    identifier = get_best_identifier_from_udm(udm_event)

    if source_severity == 30:
        return f"SpyCloud Session Cookie Theft - {identifier}"
    if source_severity == 25:
        return f"SpyCloud Malware Infection - {identifier}"
    if source_severity == 20:
        return f"SpyCloud Plaintext Credential Exposure - {identifier}"
    if source_severity == 5:
        return f"SpyCloud Informational Exposure - {identifier}"
    if source_severity == 2:
        return f"SpyCloud Email Exposure - {identifier}"

    metadata = get_udm_metadata(udm_event)
    event_type = metadata.get("event_type")
    if event_type:
        return f"SpyCloud {event_type} - {identifier}"

    return f"SpyCloud Exposure Detected - {identifier}"


def build_event_name_from_udm(udm_event: dict[str, Any]) -> str:
    source_severity = get_source_spycloud_severity(udm_event)

    if source_severity == 30:
        return "SpyCloud Session Cookie Theft"
    if source_severity == 25:
        return "SpyCloud Malware Infection"
    if source_severity == 20:
        return "SpyCloud Plaintext Credential Exposure"
    if source_severity == 5:
        return "SpyCloud Informational Exposure"
    if source_severity == 2:
        return "SpyCloud Email Exposure"

    metadata = get_udm_metadata(udm_event)
    return metadata.get("event_type") or "SpyCloud UDM Event"


def get_udm_event_time_ms(udm_event: dict[str, Any]) -> int:
    metadata = get_udm_metadata(udm_event)

    for key in ["event_timestamp", "collected_timestamp", "product_event_timestamp"]:
        parsed = parse_iso_to_unix_ms(metadata.get(key))
        if parsed:
            return parsed

    extensions = get_udm_extensions(udm_event)
    for key in [
        "infected_time",
        "spycloud_publish_date",
        "record_modification_date",
        "publish_date",
        "created_at",
        "updated_at",
    ]:
        parsed = parse_iso_to_unix_ms(extensions.get(key))
        if parsed:
            return parsed

    return int(datetime.now(timezone.utc).timestamp() * 1000)


def normalize_scalar(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, str)):
        return value
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value)


def normalize_event(event_dict: dict[str, Any]) -> dict[str, Any]:
    return {key: normalize_scalar(value) for key, value in event_dict.items()}


def flatten_udm_event_for_alert(udm_event: dict[str, Any]) -> dict[str, Any]:
    metadata = get_udm_metadata(udm_event)
    principal = get_udm_principal(udm_event)
    target = get_udm_target(udm_event)
    security_result = get_udm_security_result(udm_event)
    extensions = get_udm_extensions(udm_event)
    additional = get_udm_additional(udm_event)

    principal_user = principal.get("user") if isinstance(principal.get("user"), dict) else {}

    flattened = {
        "udm_event_type": metadata.get("event_type"),
        "udm_event_timestamp": metadata.get("event_timestamp"),
        "udm_vendor_name": metadata.get("vendor_name"),
        "udm_product_name": metadata.get("product_name"),
        "udm_product_event_type": metadata.get("product_event_type"),
        "udm_description": metadata.get("description"),

        "principal_hostname": principal.get("hostname"),
        "principal_asset_id": principal.get("asset_id"),
        "principal_ip": principal.get("ip"),
        "principal_platform": principal.get("platform"),
        "principal_userid": principal_user.get("userid"),
        "principal_user_email_addresses": principal_user.get("email_addresses"),

        "target_hostname": target.get("hostname"),
        "target_url": target.get("url"),
        "target_domain": target.get("domain"),
        "target_ip": target.get("ip"),
        "target_file_full_path": target.get("file", {}).get("full_path")
        if isinstance(target.get("file"), dict) else None,

        "security_result_severity": security_result.get("severity"),
        "security_result_category": security_result.get("category"),
        "security_result_summary": security_result.get("summary"),
        "security_result_description": security_result.get("description"),
        "security_result_risk_score": security_result.get("risk_score"),
        "security_result_criticality": security_result.get("criticality"),
        "security_result_product_severity": security_result.get("product_severity"),
        "security_result_product_priority": security_result.get("product_priority"),
        "security_result_confidence": security_result.get("confidence"),
        "security_result_threat_name": security_result.get("threat_name"),

        "spycloud_document_id": extensions.get("document_id"),
        "spycloud_source_id": extensions.get("source_id"),
        "spycloud_source_severity": extensions.get("severity"),
        "spycloud_severity_label": (
            extensions.get("spycloud_severity_label")
            or additional.get("spycloud_severity_label")
        ),
        "spycloud_mapped_soar_severity": extensions.get("soar_severity") or additional.get("soar_severity"),
        "spycloud_risk_score": extensions.get("risk_score") or additional.get("risk_score"),
        "spycloud_criticality": extensions.get("criticality") or additional.get("criticality"),

        "spycloud_email": extensions.get("email"),
        "spycloud_username": extensions.get("username"),
        "spycloud_domain": extensions.get("domain"),
        "spycloud_password_type": extensions.get("password_type"),
        "spycloud_has_password": extensions.get("has_password") or additional.get("has_password"),
        "spycloud_has_plaintext_password": (
            extensions.get("has_plaintext_password")
            or additional.get("has_plaintext_password")
        ),

        # Sensitive breach values. Only populated when the connector's "Include
        # Plaintext Secrets" option is enabled; otherwise the converter never puts
        # these into the UDM extensions and each resolves to an empty string.
        "spycloud_password": extensions.get("password"),
        "spycloud_password_plaintext": extensions.get("password_plaintext"),
        "spycloud_password_value": extensions.get("password_value"),
        "spycloud_password_raw": extensions.get("password_raw"),
        "spycloud_new_password": extensions.get("new_password"),
        "spycloud_old_password": extensions.get("old_password"),
        "spycloud_account_password": extensions.get("account_password"),
        "spycloud_credentials": extensions.get("credentials"),
        "spycloud_private_key_password": extensions.get("private_key_password"),
        "spycloud_account_secret": extensions.get("account_secret"),
        "spycloud_account_secret_question": extensions.get("account_secret_question"),
        "spycloud_api_token": extensions.get("api_token"),
        "spycloud_api_token_secret": extensions.get("api_token_secret"),
        "spycloud_cookies": extensions.get("cookies"),
        "spycloud_cookie_data": extensions.get("cookie_data"),
        "spycloud_form_cookies_data": extensions.get("form_cookies_data"),
        "spycloud_form_post_data": extensions.get("form_post_data"),
        "spycloud_cc_number": extensions.get("cc_number"),
        "spycloud_cc_code": extensions.get("cc_code"),
        "spycloud_bank_number": extensions.get("bank_number"),
        "spycloud_bank_routing_number": extensions.get("bank_routing_number"),
        "spycloud_taxid": extensions.get("taxid"),

        "spycloud_log_id": extensions.get("log_id"),
        "spycloud_infected_machine_id": extensions.get("infected_machine_id"),
        "spycloud_infected_time": extensions.get("infected_time"),
        "spycloud_record_modification_date": extensions.get("record_modification_date"),
        "spycloud_record_cracked_date": extensions.get("record_cracked_date"),
        "spycloud_record_addition_date": extensions.get("record_addition_date"),
        "spycloud_infected_path": extensions.get("infected_path"),
        "spycloud_target_url": extensions.get("target_url"),
        "spycloud_target_domain": extensions.get("target_domain"),
        "spycloud_target_subdomain": extensions.get("target_subdomain"),
        "spycloud_user_hostname": extensions.get("user_hostname"),
        "spycloud_user_os": extensions.get("user_os"),
        "spycloud_user_browser": extensions.get("user_browser"),
        "spycloud_user_agent": extensions.get("user_agent"),
        "spycloud_country_code": extensions.get("country_code"),
        "spycloud_timezone": extensions.get("timezone"),

        "spycloud_breach_title": first_present(extensions, ["title", "short_title"]),
        "spycloud_breach_site": extensions.get("site"),
        "spycloud_breach_main_category": extensions.get("breach_main_category"),
        "spycloud_breach_category": extensions.get("breach_category"),
        "spycloud_malware_family": extensions.get("malware_family"),
        "spycloud_confidence": extensions.get("confidence"),
        "spycloud_tlp": extensions.get("tlp"),
        "spycloud_collection_source": (
            extensions.get("spycloud_collection_source")
            or additional.get("spycloud_collection_source")
        ),
        "spycloud_merged_record_count": (
            extensions.get("_merged_record_count")
            or additional.get("_merged_record_count")
        ),
    }

    return normalize_event(flattened)


def build_alert_from_udm_event(
    udm_event: dict[str, Any],
    environment_common: Any = None,
    device_product_field: str | None = None,
) -> AlertInfo:
    event_time_ms = get_udm_event_time_ms(udm_event)
    mapped_severity = get_mapped_alert_severity(udm_event)
    risk_score = get_udm_risk_score(udm_event)
    criticality = get_udm_criticality(udm_event)

    alert = AlertInfo()
    alert_id = build_stable_alert_id_from_udm(udm_event)

    alert.display_id = alert_id
    alert.ticket_id = alert_id
    alert.name = build_alert_name_from_udm(udm_event)
    alert.rule_generator = build_rule_generator_from_udm(udm_event)
    alert.start_time = event_time_ms
    alert.end_time = event_time_ms
    alert.priority = map_priority_from_mapped_severity(mapped_severity)
    alert.severity = alert.priority
    alert.device_vendor = VENDOR

    flattened = flatten_udm_event_for_alert(udm_event)

    # Resolve the device product from the configured field name (falling back to
    # the integration product), mirroring the convention used by other connectors.
    device_product = None
    if device_product_field:
        device_product = flattened.get(device_product_field)
    device_product = device_product or PRODUCT
    alert.device_product = device_product

    event = {
        "StartTime": event_time_ms,
        "EndTime": event_time_ms,
        "event_name": build_event_name_from_udm(udm_event),
        "device_product": device_product,
        "severity": mapped_severity if mapped_severity is not None else "",
        "risk_score": risk_score if risk_score is not None else "",
        "criticality": criticality,
        "udm_event": json.dumps(udm_event, sort_keys=True, default=str),
        **flattened,
    }

    # Resolve the alert environment from the event payload when an environment
    # manager is supplied; otherwise the platform default environment is used.
    if environment_common is not None:
        alert.environment = environment_common.get_environment(event)

    alert.events.append(event)
    return alert