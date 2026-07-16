"""ELLIO - Add IP to Blocklist. POSTs IP addresses to ELLIO Blocklist Automation."""
from __future__ import annotations

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED, EXECUTION_STATE_FAILED
from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import convert_dict_to_json_result_dict, output_handler
from TIPCommon.extraction import extract_action_param

from ..core.action_utils import collect_target_ips, config_reader
from ..core.constants import DEFAULT_ELLIO_API_ROOT, ENRICH_PREFIX, INTEGRATION_NAME
from ..core.ellio_manager import EllioManager, EllioManagerError

SCRIPT_NAME = "Add IP to Blocklist"


@output_handler
def main() -> None:
    """Add IP addresses to the configured ELLIO blocklist ruleset."""
    siemplify = SiemplifyAction()
    siemplify.script_name = f"{INTEGRATION_NAME} - {SCRIPT_NAME}"
    siemplify.LOGGER.info("================= Main - Param Init =================")

    cfg = config_reader(siemplify)
    ellio_api_root = cfg(param_name="API Root", default_value=DEFAULT_ELLIO_API_ROOT, input_type=str)
    ellio_api_key = cfg(param_name="API Key", is_mandatory=True, input_type=str)
    ruleset_id = cfg(param_name="Blocklist Ruleset ID", is_mandatory=False, input_type=str)
    verify_ssl = cfg(param_name="Verify SSL", default_value=True, input_type=bool)

    ip_csv = extract_action_param(siemplify, param_name="IP Addresses", is_mandatory=False,
                                  input_type=str, default_value="", print_value=True)
    rule_name = extract_action_param(siemplify, param_name="Rule Name", is_mandatory=False,
                                     input_type=str, default_value="", print_value=True)
    expires_in_days = extract_action_param(siemplify, param_name="Expires In Days", is_mandatory=False,
                                           input_type=int, default_value=14, print_value=True)
    conflict_resolution = extract_action_param(siemplify, param_name="Conflict Resolution", is_mandatory=False,
                                               input_type=str, default_value="extend", print_value=True)

    siemplify.LOGGER.info("----------------- Main - Started -----------------")

    if not ruleset_id:
        siemplify.end('Error executing action "Add IP to Blocklist". Reason: '
                      "Blocklist Ruleset ID is not configured.", False, EXECUTION_STATE_FAILED)
        return

    manager = EllioManager(ellio_api_root=ellio_api_root, ellio_api_key=ellio_api_key,
                           blocklist_ruleset_id=ruleset_id, verify_ssl=verify_ssl)

    # shared guard: never blocklist a SOAR-internal entity or a private/reserved
    # address - pushing the organization's own IP is a self-inflicted outage
    target_ips, entity_by_ip, skipped = collect_target_ips(siemplify, ip_csv)
    if skipped:
        siemplify.LOGGER.info(f"Skipped internal/non-public addresses (not blocklisted): {', '.join(skipped)}")

    # auto rule-name context: the case + the alert/rule that fired (the per-IP ELLIO
    # classification is appended when Enrich IP ran first and left ELLIO_classification).
    # Emitted as parsable `key=value | key=value` (split on ' | ', then on the first '=').
    case_ref = f"secops_case={siemplify.case_id}"
    try:
        alert = siemplify.current_alert
        alert_name = (getattr(alert, "name", None) or getattr(alert, "rule_generator", None) or "").strip()
    except Exception as error:  # noqa: BLE001
        siemplify.LOGGER.info(f"No current alert available: {error}")
        alert_name = ""

    def rule_label(ip: str) -> str:
        """Rule name for `ip`: the given override, or parsable case context.

        Args:
            ip: The IP address the rule is created for.

        Returns:
            The rule name.
        """
        if rule_name:
            return rule_name
        parts = [case_ref]
        if alert_name:
            parts.append(f"alert={alert_name}")
        entity = entity_by_ip.get(ip)
        props = (getattr(entity, "additional_properties", None) or {}) if entity else {}
        classification = props.get(f"{ENRICH_PREFIX}classification") or ""
        if classification:
            parts.append(f"ellio={classification}")
        return " | ".join(parts)

    json_results, successful, failed, errors = {}, [], [], []
    for ip in target_ips:
        try:
            json_results[ip] = manager.add_ip_to_blocklist(
                ip, name=rule_label(ip),
                conflict_resolution=conflict_resolution, expires_in_days=expires_in_days)
            successful.append(ip)
        except EllioManagerError as error:
            failed.append(ip)
            errors.append(str(error))
            json_results[ip] = {"ip": ip, "status": "failed", "error": str(error)}
            siemplify.LOGGER.error(f"Failed to add {ip}: {error}")
    for ip in skipped:
        json_results[ip] = {"ip": ip, "status": "skipped", "reason": "SOAR-internal or not a public IP"}

    # Report added / failed (with the reason, e.g. a 403 read_write permission error so a
    # failed write is never a silent no-op) / skipped-by-guard.
    parts = []
    if successful:
        parts.append(f"added {', '.join(successful)}")
    if failed:
        parts.append(f"failed {', '.join(failed)}" + (f" ({errors[0]})" if errors else ""))
    if skipped:
        parts.append(f"skipped {', '.join(skipped)} (internal or not public)")
    output_message = ("ELLIO blocklist: " + "; ".join(parts) + "." if parts
                      else "No IP Address entities or IP parameters were provided.")

    siemplify.result.add_result_json(convert_dict_to_json_result_dict(json_results))
    siemplify.LOGGER.info("----------------- Main - Finished -----------------")
    # A blocklist write that fully failed (read-only key -> 403, or the API unreachable) ends
    # FAILED so a playbook can branch on it; a partial success or a skip-only run completes.
    if successful:
        status = EXECUTION_STATE_COMPLETED
    elif failed:
        status = EXECUTION_STATE_FAILED
    else:
        status = EXECUTION_STATE_COMPLETED
    siemplify.end(output_message, bool(successful), status)


if __name__ == "__main__":
    main()
