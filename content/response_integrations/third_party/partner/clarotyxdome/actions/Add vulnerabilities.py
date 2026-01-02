from SiemplifyAction import SiemplifyAction
from SiemplifyUtils import output_handler
from TIPCommon.extraction import extract_configuration_param
import requests
import re

ALL_ENRICH_FIELDS = [
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

VULN_FIELDS = [
    "device_uid",
    "device_category",
    "device_subcategory",
    "device_type",
    "device_risk_score",
    "device_assignees",
    "device_labels",
    "device_site_name",
    "vulnerability_id",
    "vulnerability_name",
    "vulnerability_type",
    "vulnerability_cve_ids",
    "vulnerability_adjusted_vulnerability_score",
    "vulnerability_epss_score",
    "vulnerability_sources",
    "vulnerability_description",
    "vulnerability_affected_products",
    "vulnerability_recommendations",
    "vulnerability_is_known_exploited",
    "vulnerability_published_date",
    "vulnerability_labels",
    "vulnerability_assignees",
    "vulnerability_note",
    "vulnerability_last_updated",
    "vulnerability_relevance",
    "vulnerability_relevance_sources",
    "device_vulnerability_detection_date",
    "device_vulnerability_resolution_date",
    "device_vulnerability_days_to_resolution",
    "patch_install_date",
]


def is_likely_uid(identifier):
    return bool(re.match(r"^[a-f0-9\-]{32,40}$", identifier, re.IGNORECASE))


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


def get_devices_for_identifier(
    identifier, api_root, api_token, fields=None, verify_ssl=True, timeout=5
):
    field, operation, value = build_filter(identifier)
    if not field:
        return []
    url = f"{api_root.rstrip('/')}/api/v1/devices/"
    if not fields:
        fields = ["uid", "device_name", "ip_list"]
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
    resp = requests.post(url, headers=headers, json=payload, verify=verify_ssl, timeout=timeout)
    resp.raise_for_status()
    return resp.json().get("devices", [])


def get_vuln_by_uid(device_uid, api_root, api_token, fields=None, verify_ssl=True, timeout=5):
    url = f"{api_root.rstrip('/')}/api/v1/device_vulnerability_relations/"
    if not fields:
        fields = ["vulnerability_id", "vulnerability_name"]
    payload = {
        "filter_by": {"field": "device_uid", "operation": "equals", "value": device_uid},
        "fields": fields,
        "offset": 0,
        "limit": 100,
    }
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, verify=verify_ssl, timeout=timeout)
    resp.raise_for_status()
    response_json = resp.json()
    results = response_json.get("devices_vulnerabilities", [])
    return results


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
    verify_ssl = extract_configuration_param(
        siemplify,
        provider_name="Claroty xDome",
        param_name="Verify SSL",
        is_mandatory=False,
        input_type=bool,
        print_value=True,
    )
    timeout = 5

    successful_entities = []
    failed_entities = []
    json_results = {}

    for entity in siemplify.target_entities:
        identifier = entity.identifier
        try:
            if is_likely_uid(identifier):
                device_uid = identifier
            else:
                devices = get_devices_for_identifier(
                    identifier,
                    api_root,
                    api_token,
                    fields=ALL_ENRICH_FIELDS,
                    verify_ssl=verify_ssl,
                    timeout=timeout,
                )
                if devices:
                    device_uid = devices[0].get("uid")
                else:
                    failed_entities.append(entity)
                    json_results[identifier] = {"error": "No device found for this identifier."}
                    continue
            vulnerabilities = get_vuln_by_uid(
                device_uid,
                api_root,
                api_token,
                fields=VULN_FIELDS,
                verify_ssl=verify_ssl,
                timeout=timeout,
            )
            enrichment_data = {
                "vulnerabilities": vulnerabilities,
                "vulnerability_count": len(vulnerabilities),
                "device_uid": device_uid,
                "is_vulnerable": len(vulnerabilities) > 0,
            }
            entity.additional_properties.update(enrichment_data)
            entity.is_enriched = True
            successful_entities.append(entity)
            json_results[identifier] = enrichment_data
        except Exception as e:
            failed_entities.append(entity)
            json_results[identifier] = {"error": str(e)}

    if successful_entities:
        try:
            siemplify.update_entities(successful_entities)
        except Exception:
            pass

    output_message = ""
    status = False

    if successful_entities:
        output_message = "Successfully enriched devices:\n" + "\n".join([
            e.identifier for e in successful_entities
        ])
        status = True
    else:
        output_message = "No devices were successfully enriched."

    if failed_entities:
        output_message += "\n\nFailed to enrich:\n" + "\n".join([
            e.identifier for e in failed_entities
        ])

    siemplify.result.add_result_json(json_results)
    siemplify.end(output_message, str(status), status)


if __name__ == "__main__":
    main()
