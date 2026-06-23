"""
UpdateAlertSeverity — SecOps action that writes a severity change back to Cyble.

Parameters:
  - Cyble Alert ID  (auto-populated from the AlertId custom field)
  - Cyble Service   (auto-populated from the Service custom field)
  - New Severity    (dropdown: CRITICAL | HIGH | MEDIUM | LOW)

Accepts both SecOps string severities and SecOps integer severities
(e.g., "-1" = CRITICAL, "2" = HIGH) so playbook mappings work without
string conversion blocks.
"""
from __future__ import annotations

from datetime import datetime, timezone

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    FIELD_ALERT_ID,
    FIELD_LAST_SYNC_AT,
    FIELD_SERVICE,
    FIELD_SEVERITY,
    INTEGRATION_NAME,
    PARAM_API_KEY,
    PARAM_BASE_URL,
    PARAM_TIMEOUT,
    PARAM_VERIFY_SSL,
    SECOPS_TO_CYBLE_SEVERITY,
)
from ..core.CybleAlertMapper import CybleAlertMapper
from ..core.CybleManager import (
    CybleAPIError,
    CybleAuthError,
    CybleManager,
    CybleNotFoundError,
    CybleValidationError,
)

SCRIPT_NAME = "UpdateAlertSeverity"
PARAM_ALERT_ID = "Cyble Alert ID"
PARAM_SERVICE = "Cyble Service"
PARAM_NEW_SEVERITY = "New Severity"

VALID_SEVERITIES = list(SECOPS_TO_CYBLE_SEVERITY.keys())  # CRITICAL, HIGH, MEDIUM, LOW


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_API_KEY, is_mandatory=True
    )
    base_url = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_BASE_URL, default_value=DEFAULT_BASE_URL
    )
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_VERIFY_SSL,
        input_type=bool, default_value=True
    )
    timeout = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_TIMEOUT,
        input_type=int, default_value=DEFAULT_TIMEOUT
    )

    cyble_alert_id = (
        siemplify.extract_action_param(param_name=PARAM_ALERT_ID, is_mandatory=False)
        or siemplify.current_alert.additional_properties.get(FIELD_ALERT_ID)
    )
    service = (
        siemplify.extract_action_param(param_name=PARAM_SERVICE, is_mandatory=False)
        or siemplify.current_alert.additional_properties.get(FIELD_SERVICE)
    )
    new_severity = siemplify.extract_action_param(param_name=PARAM_NEW_SEVERITY, is_mandatory=True)

    # ── Validation ────────────────────────────────────────────────────────────
    errors = []
    if not cyble_alert_id:
        errors.append(f"'{PARAM_ALERT_ID}' could not be resolved from action params or alert fields.")
    if not service:
        errors.append(f"'{PARAM_SERVICE}' could not be resolved from action params or alert fields.")

    # Normalise integer severity input (SecOps passes integers in some playbook contexts)
    normalised_severity = new_severity
    if new_severity and new_severity.strip().lstrip("-").isdigit():
        from ..core.constants import SECOPS_INT_TO_CYBLE_SEVERITY
        normalised_severity = SECOPS_INT_TO_CYBLE_SEVERITY.get(int(new_severity), "MEDIUM")

    if normalised_severity and normalised_severity.upper() not in VALID_SEVERITIES:
        errors.append(
            f"'{new_severity}' is not a valid severity. Valid values: {VALID_SEVERITIES}"
        )

    if errors:
        msg = "Validation failed: " + "; ".join(errors)
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] {msg}")
        siemplify.end(msg, "false")
        return

    try:
        update_payload = CybleAlertMapper.secops_to_cyble_update(
            cyble_alert_id=cyble_alert_id,
            service=service,
            new_severity=normalised_severity,
        )
    except ValueError as e:
        siemplify.end(str(e), "false")
        return

    try:
        manager = CybleManager(
            api_key=api_key, base_url=base_url, verify_ssl=verify_ssl, timeout=timeout
        )
        manager.update_alerts([update_payload])

    except CybleNotFoundError:
        siemplify.end(
            f"Alert '{cyble_alert_id}' not found in Cyble (may have been deleted).", "false"
        )
        return
    except (CybleAuthError, CybleValidationError, CybleAPIError) as e:
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] API error: {e}")
        siemplify.end(str(e), "false")
        return

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    success_msg = (
        f"Successfully updated alert '{cyble_alert_id}' (service: {service}) "
        f"severity to '{normalised_severity}' in Cyble Vision Alerts."
    )
    siemplify.LOGGER.info(f"[{SCRIPT_NAME}] {success_msg}")

    try:
        siemplify.update_alert_additional_data(
            alert_id=siemplify.current_alert.identifier,
            additional_data={
                FIELD_SEVERITY:     normalised_severity.upper(),
                FIELD_LAST_SYNC_AT: now_iso,
            },
        )
        siemplify.add_comment(
            comment=f"[Update] {success_msg}",
            case_id=siemplify.case.identifier,
        )
    except Exception as e:  # noqa: BLE001
        siemplify.LOGGER.info(f"[{SCRIPT_NAME}] [WARN] Local field update failed (non-fatal): {e}")

    siemplify.end(success_msg, "true")


if __name__ == "__main__":
    main()
