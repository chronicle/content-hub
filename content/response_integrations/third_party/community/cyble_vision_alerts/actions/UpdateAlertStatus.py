"""
UpdateAlertStatus — SecOps action that writes a status change back to Cyble.

Called from:
  - Playbooks (automated): when an analyst closes/triages a case.
  - Manual: from the action panel on a Cyble-sourced alert.

Parameters:
  - Cyble Alert ID  (auto-populated from the AlertId custom field if mapped)
  - Cyble Service   (auto-populated from the Service custom field)
  - New Status      (dropdown: UNREVIEWED | VIEWED | UNDER_REVIEW |
                     CONFIRMED_INCIDENT | INFORMATIONAL | RESOLVED)

On success:
  - Adds an audit comment to the SecOps case wall.
  - Updates the Status and LastSyncAt custom fields on the alert.

On failure:
  - Raises an exception so the playbook can route to an error branch.
  - Does NOT silently swallow errors.
"""
from __future__ import annotations

from datetime import datetime, timezone

from soar_sdk.SiemplifyAction import SiemplifyAction
from soar_sdk.SiemplifyUtils import output_handler

from ..core.constants import (
    CYBLE_STATUSES,
    DEFAULT_BASE_URL,
    DEFAULT_TIMEOUT,
    FIELD_ALERT_ID,
    FIELD_LAST_SYNC_AT,
    FIELD_SERVICE,
    FIELD_STATUS,
    INTEGRATION_NAME,
    PARAM_API_KEY,
    PARAM_BASE_URL,
    PARAM_TIMEOUT,
    PARAM_VERIFY_SSL,
)
from ..core.CybleAlertMapper import CybleAlertMapper
from ..core.CybleManager import (
    CybleAPIError,
    CybleAuthError,
    CybleManager,
    CybleNotFoundError,
    CybleValidationError,
)

SCRIPT_NAME = "UpdateAlertStatus"
PARAM_ALERT_ID = "Cyble Alert ID"
PARAM_SERVICE = "Cyble Service"
PARAM_NEW_STATUS = "New Status"


@output_handler
def main():
    siemplify = SiemplifyAction()
    siemplify.script_name = SCRIPT_NAME

    # ── Load integration config ───────────────────────────────────────────────
    api_key = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_API_KEY, is_mandatory=True
    )
    base_url = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_BASE_URL,
        default_value=DEFAULT_BASE_URL
    )
    verify_ssl = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_VERIFY_SSL,
        input_type=bool, default_value=True
    )
    timeout = siemplify.extract_configuration_param(
        provider_name=INTEGRATION_NAME, param_name=PARAM_TIMEOUT,
        input_type=int, default_value=DEFAULT_TIMEOUT
    )

    # ── Load action parameters ────────────────────────────────────────────────
    # Try action param first; fall back to alert custom field
    cyble_alert_id = (
        siemplify.extract_action_param(param_name=PARAM_ALERT_ID, is_mandatory=False)
        or siemplify.current_alert.additional_properties.get(FIELD_ALERT_ID)
    )
    service = (
        siemplify.extract_action_param(param_name=PARAM_SERVICE, is_mandatory=False)
        or siemplify.current_alert.additional_properties.get(FIELD_SERVICE)
    )
    new_status = siemplify.extract_action_param(param_name=PARAM_NEW_STATUS, is_mandatory=True)

    # ── Input validation ──────────────────────────────────────────────────────
    errors = []
    if not cyble_alert_id:
        errors.append(
            f"'{PARAM_ALERT_ID}' is required. Ensure the alert has '{FIELD_ALERT_ID}' "
            "populated or provide it explicitly."
        )
    if not service:
        errors.append(
            f"'{PARAM_SERVICE}' is required. Ensure the alert has '{FIELD_SERVICE}' "
            "populated or provide it explicitly."
        )
    if new_status and new_status.upper() not in CYBLE_STATUSES:
        errors.append(
            f"'{new_status}' is not a valid Cyble status. "
            f"Valid values: {CYBLE_STATUSES}"
        )
    if errors:
        msg = "Validation failed: " + "; ".join(errors)
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] {msg}")
        siemplify.end(msg, "false")
        return

    # ── Build update payload ──────────────────────────────────────────────────
    try:
        update_payload = CybleAlertMapper.secops_to_cyble_update(
            cyble_alert_id=cyble_alert_id,
            service=service,
            new_status=new_status,
        )
    except ValueError as e:
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] Payload error: {e}")
        siemplify.end(str(e), "false")
        return

    # ── Call Cyble API ────────────────────────────────────────────────────────
    try:
        manager = CybleManager(
            api_key=api_key, base_url=base_url, verify_ssl=verify_ssl, timeout=timeout
        )
        manager.update_alerts([update_payload])

    except CybleNotFoundError:
        msg = (
            f"Alert '{cyble_alert_id}' not found in Cyble. "
            "It may have been deleted or the ID is incorrect."
        )
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] {msg}")
        siemplify.end(msg, "false")
        return

    except CybleValidationError as e:
        msg = f"Cyble rejected the update request: {e}"
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] {msg}")
        siemplify.end(msg, "false")
        return

    except CybleAuthError as e:
        msg = f"Authentication failed — check API key: {e}"
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] {msg}")
        siemplify.end(msg, "false")
        return

    except CybleAPIError as e:
        msg = f"Cyble API error: {e}"
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] {msg}")
        siemplify.end(msg, "false")
        return

    # ── Post-success: audit trail ─────────────────────────────────────────────
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    success_msg = (
        f"Successfully updated alert '{cyble_alert_id}' (service: {service}) "
        f"status to '{new_status}' in Cyble Vision Alerts."
    )
    siemplify.LOGGER.info(f"[{SCRIPT_NAME}] {success_msg}")

    # Update custom fields on the SecOps alert for sync visibility
    try:
        siemplify.update_alert_additional_data(
            alert_id=siemplify.current_alert.identifier,
            additional_data={
                FIELD_STATUS:        new_status.upper(),
                FIELD_LAST_SYNC_AT:  now_iso,
            },
        )
        siemplify.add_comment(
            comment=f"[Update] {success_msg}",
            case_id=siemplify.case.identifier,
        )
    except Exception as e:  # noqa: BLE001
        # Non-fatal — the Cyble update succeeded; only the local bookkeeping failed
        siemplify.LOGGER.info(
            f"[{SCRIPT_NAME}] [WARN] Cyble updated successfully but failed to update "
            f"local alert fields: {e}"
        )

    siemplify.end(success_msg, "true")


if __name__ == "__main__":
    main()
