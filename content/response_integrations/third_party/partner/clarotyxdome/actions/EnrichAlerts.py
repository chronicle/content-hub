from SiemplifyAction import SiemplifyAction
from TIPCommon.extraction import extract_configuration_param
import requests
import json

CLAROTY_ALERT_FIELDS = [
    "id",
    "alert_name",
    "alert_type_name",
    "alert_class",
    "category",
    "detected_time",
    "updated_time",
    "status",
    "description",
    "mitre_technique_ics_ids",
    "mitre_technique_ics_names",
    "mitre_technique_enterprise_ids",
    "mitre_technique_enterprise_names",
    "malicious_ip_tags_list",
]


def get_alert_details(api_root, api_token, alert_id, fields=None, verify_ssl=True):
    url = f"{api_root.rstrip('/')}/api/v1/alerts/"
    payload = {
        "filter_by": {"field": "id", "operation": "equals", "value": int(alert_id)},
        "offset": 0,
        "limit": 1,
        "fields": fields or CLAROTY_ALERT_FIELDS,
    }
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=payload, verify=True)
    resp.raise_for_status()
    return resp.json().get("alerts", [])


def enrich_alert_with_fields(siemplify_alert, claroty_alert, prefix="Claroty_"):
    for k, v in claroty_alert.items():
        if k in CLAROTY_ALERT_FIELDS:
            siemplify_alert.additional_properties[f"{prefix}{k}"] = (
                json.dumps(v) if isinstance(v, (list, dict)) else str(v)
            )

    sr = getattr(siemplify_alert, "security_result", None)
    if isinstance(sr, list) and sr:
        mitre_names = claroty_alert.get("mitre_technique_enterprise_names") or claroty_alert.get(
            "mitre_technique_ics_names"
        )
        mitre_ids = claroty_alert.get("mitre_technique_enterprise_ids") or claroty_alert.get(
            "mitre_technique_ics_ids"
        )
        tactic_name = mitre_names[0] if isinstance(mitre_names, list) and mitre_names else ""
        technique_name = (
            mitre_names if isinstance(mitre_names, list) and len(mitre_names) > 1 else ""
        )
        tactic_id = mitre_ids[0] if isinstance(mitre_ids, list) and mitre_ids else ""
        technique_id = mitre_ids if isinstance(mitre_ids, list) and len(mitre_ids) > 1 else ""
        if tactic_name:
            sr[0]["tactic"] = tactic_name
        if tactic_id:
            sr[0]["tactic_id"] = tactic_id
        if technique_name:
            sr[0]["technique"] = technique_name
        if technique_id:
            sr[0]["technique_id"] = technique_id


def main():
    siemplify = SiemplifyAction()
    result_json = {}
    output_lines = []
    status_ok = False

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

    alert_id_str = siemplify.extract_action_param("clarotyAlertId", is_mandatory=True)
    output_lines.append(f"Requesting Claroty alert id: {alert_id_str}")

    try:
        alerts = get_alert_details(
            api_root, api_token, alert_id=alert_id_str, fields=CLAROTY_ALERT_FIELDS, verify_ssl=True
        )
        if not alerts:
            output_message = f"No Claroty alert found for id {alert_id_str}."
            status_ok = False
        else:
            alert = alerts[0]
            result_json[str(alert.get("id"))] = alert
            output_lines.append(
                f"Alert: {alert.get('id')} | Name: {alert.get('alert_name')} | "
                f"Status: {alert.get('status')}"
            )
            if hasattr(siemplify, "current_alert"):
                enrich_alert_with_fields(siemplify.current_alert, alert)
            output_message = "Enriched Siemplify alert with Claroty alert and MITRE information."
            status_ok = True
    except Exception as e:
        output_message = f"Failed to get Claroty alert details: {e}"
        status_ok = False

    siemplify.result.add_result_json(result_json)
    siemplify.end(
        output_message + ("\n\n" + "\n".join(output_lines) if output_lines else ""), status_ok
    )


if __name__ == "__main__":
    main()
