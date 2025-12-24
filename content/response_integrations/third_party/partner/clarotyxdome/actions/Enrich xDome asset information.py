from SiemplifyAction import SiemplifyAction
from SiemplifyDataModel import EntityTypes
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param
import requests
import re

SAFE_DEVICE_FIELDS = [
    "uid",
    "device_name",
    "ip_list",
    "mac_list",
    "site_name",
    "risk_score",
    "manufacturer",
    "device_category",
    "device_type",
    "device_subcategory",
]

ALL_ENRICH_FIELDS = [
    "device_category",
    "device_subcategory",
    "device_type",
    "internet_communication",
    "device_name",
    "manufacturer",
    "site_name",
    "risk_score",
    "risk_score_points",
    "known_vulnerabilities",
    "software_or_firmware_version",
    "ip_list",
    "mac_list",
]

VULN_FIELDS = [
    "device_uid",
    "vulnerability_id",
    "vulnerability_name",
    "vulnerability_cve_ids",
    "vulnerability_published_date",
]


def build_filter(identifier):
    ip_regex = r"^(\d{1,3}\.){3}\d{1,3}$"
    ip6_regex = r"([a-fA-F\d]{1,4}:){7}[a-fA-F\d]{1,4}"
    mac_regex = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
    if re.match(ip_regex, identifier) or re.match(ip6_regex, identifier):
        return "ip_list", "equals", identifier
    elif re.match(mac_regex, identifier):
        return "mac_list", "equals", identifier.upper()
    else:
        return None, None, None


def get_devices_for_identifier(identifier, api_root, api_token, logger, fields=None, timeout=15):
    field, operation, value = build_filter(identifier)
    if not field:
        return []
    url = f"{api_root.rstrip('/')}/api/v1/devices/"
    if not fields:
        fields = SAFE_DEVICE_FIELDS
    payload = {
        "filter_by": {
            "operation": "and",
            "operands": [
                {"field": field, "operation": operation, "value": value},
                {"field": "retired", "operation": "in", "value": [False]},
            ],
        },
        "fields": fields,
        "offset": 0,
        "limit": 5,
    }
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, verify=True, timeout=timeout)
    resp.raise_for_status()
    devices = resp.json().get("devices", [])
    logger.info(f"Claroty API: Queried {identifier}, got {len(devices)} device(s).")
    return devices


def compact_enrichment(device, prefix="Claroty_", max_list_items=3):
    compact = {}
    for k in SAFE_DEVICE_FIELDS:
        v = device.get(k)
        key = f"{prefix}{k}"
        if isinstance(v, list):
            vals = [str(i) for i in v if i is not None]
            compact[key] = ", ".join(vals[:max_list_items])
        elif v is not None:
            compact[key] = str(v)
    return compact


def get_vuln_by_uid(device_uid, api_root, api_token, logger=None, fields=None, timeout=15):
    url = f"{api_root.rstrip('/')}/api/v1/device_vulnerability_relations/"
    if not fields:
        fields = VULN_FIELDS
    payload = {
        "filter_by": {"field": "device_uid", "operation": "equals", "value": device_uid},
        "fields": fields,
        "offset": 0,
        "limit": 100,
    }
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, verify=True, timeout=timeout)
    if logger:
        logger.info(f"Vuln API status: {resp.status_code} | text: {resp.text[:256]}")
    resp.raise_for_status()
    response_json = resp.json()
    return response_json.get("devices_vulnerabilities", [])


def summarize_vulns(vulns, max_entries=5):
    summary = []
    for vuln in vulns[:max_entries]:
        summary.append(
            f"{vuln.get('vulnerability_name', '')} "
            f"({', '.join(vuln.get('vulnerability_cve_ids', []))})"
        )
    return "; ".join(summary)


@output_handler
def main():
    siemplify = SiemplifyAction()
    api_root = extract_configuration_param(
        siemplify,
        provider_name="Claroty xDome",
        param_name="xdomeHost",
        is_mandatory=True,
        print_value=True,
    )
    api_token = extract_configuration_param(
        siemplify,
        provider_name="Claroty xDome",
        param_name="xdomeApiToken",
        is_mandatory=True,
        print_value=False,
    )
    successful_entities = []
    failed_entities = []
    output_json = {}

    for entity in siemplify.target_entities:
        if entity.entity_type not in [EntityTypes.ADDRESS, EntityTypes.MACADDRESS]:
            failed_entities.append(entity)
            output_json[entity.identifier] = {"error": "Unsupported entity type"}
            continue
        identifier = entity.identifier
        field, _, _ = build_filter(identifier)
        if not field:
            failed_entities.append(entity)
            output_json[identifier] = {"error": "Not an IP or MAC address"}
            continue
        try:
            devices = get_devices_for_identifier(
                identifier, api_root, api_token, siemplify.LOGGER, fields=ALL_ENRICH_FIELDS
            )
            if not devices:
                failed_entities.append(entity)
                output_json[identifier] = {"error": "No matching device found"}
                continue
            device = devices[0]
            compact = compact_enrichment(device)
            device_uid = device.get("uid")
            vulnerabilities = get_vuln_by_uid(
                device_uid, api_root, api_token, logger=siemplify.LOGGER
            )
            vuln_count = len(vulnerabilities)
            top_vulns = summarize_vulns(vulnerabilities, max_entries=5)
            compact["vulnerability_count"] = vuln_count
            compact["top_vulns"] = top_vulns
            compact["is_vulnerable"] = vuln_count > 0
            entity.additional_properties.update(compact)
            entity.is_enriched = True
            output_json[identifier] = compact
            successful_entities.append(entity)
        except Exception as e:
            failed_entities.append(entity)
            output_json[identifier] = {"error": str(e)}

    if successful_entities:
        try:
            siemplify.update_entities(successful_entities)
        except Exception:
            pass

    if successful_entities:
        output_message = "Successfully enriched the following entities:\n" + "\n".join([
            e.identifier for e in successful_entities
        ])
        status = True
    else:
        output_message = "No assets were enriched."
        status = False

    if failed_entities:
        output_message += "\n\nFailed to enrich:\n" + "\n".join([
            e.identifier for e in failed_entities
        ])

    siemplify.result.add_result_json(output_json)
    siemplify.end(output_message, status)


if __name__ == "__main__":
    main()
