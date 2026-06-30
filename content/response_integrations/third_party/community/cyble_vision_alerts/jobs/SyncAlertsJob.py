"""
SyncAlertsJob — scheduled SOAR job that refreshes EXISTING cases.

This job runs alongside CybleVisionConnector. The connector handles new-case
creation; this job handles the bidirectional drift from Cyble back into SOAR:

  - When an analyst inside the Cyble portal changes a status (e.g. UNREVIEWED -> VIEWED)
    or a severity, the Cyble alert's `updated_at` advances. This job re-fetches the
    same alerts as the connector, BUT only for purposes of refreshing existing SOAR
    cases' custom fields (Status / Severity / LastSyncAt) when the
    Cyble-side `updated_at` is newer than our last sync.

  - It does NOT create new cases. SOAR's Job SDK does not expose case-creation APIs;
    only Connectors can. If a Cyble alert is observed here that doesn't exist in
    SOAR yet, it is logged and skipped — the Connector will pick it up on its
    own cycle.

If the running SOAR build does not expose `get_cases_by_filter` or
`update_alert_additional_data`, the job degrades gracefully — it logs a warning
once and exits cleanly without raising. In that build, drift refresh is unsupported
and analysts must trigger updates via the UpdateAlertStatus / UpdateAlertSeverity
manual actions instead.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from soar_sdk.SiemplifyJob import SiemplifyJob

from ..core.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_HOURS_BACK,
    DEFAULT_MAX_PER_CYCLE,
    DEFAULT_TIMEOUT,
    FIELD_ALERT_ID,
    FIELD_LAST_SYNC_AT,
    FIELD_SEVERITY,
    FIELD_STATUS,
    INTEGRATION_NAME,
    PARAM_API_KEY,
    PARAM_BASE_URL,
    PARAM_HOURS_BACK,
    PARAM_MAX_PER_CYCLE,
    PARAM_SERVICES,
    PARAM_TIMEOUT,
    PARAM_VERIFY_SSL,
    STATE_KEY_LAST_RUN_PREFIX,
)
from ..core.CybleAlertMapper import CybleAlertMapper
from ..core.CybleManager import CybleAPIError, CybleAuthError, CybleManager

SCRIPT_NAME = "CybleSyncAlertsJob"

logger = logging.getLogger(SCRIPT_NAME)

# Module-level capability flags — probed once per job run.
_DEDUP_LOOKUP_AVAILABLE = None  # None = unprobed, True/False = decided
_UPDATE_API_AVAILABLE = None


def main():
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME

    api_key = siemplify.extract_job_param(PARAM_API_KEY, is_mandatory=True)
    base_url = siemplify.extract_job_param(PARAM_BASE_URL, default_value=DEFAULT_BASE_URL)
    verify_ssl = siemplify.extract_job_param(PARAM_VERIFY_SSL, input_type=bool, default_value=True)
    timeout = siemplify.extract_job_param(PARAM_TIMEOUT, input_type=int, default_value=DEFAULT_TIMEOUT)
    max_per_cycle = siemplify.extract_job_param(
        PARAM_MAX_PER_CYCLE, input_type=int, default_value=DEFAULT_MAX_PER_CYCLE
    )
    hours_back = siemplify.extract_job_param(PARAM_HOURS_BACK, input_type=int, default_value=DEFAULT_HOURS_BACK)
    services_filter = siemplify.extract_job_param(PARAM_SERVICES, default_value="")

    siemplify.LOGGER.info(f"[{SCRIPT_NAME}] Job started (refresh-existing-cases mode).")

    try:
        manager = CybleManager(
            api_key=api_key,
            base_url=base_url,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
    except CybleAuthError as e:
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] Auth configuration error: {e}")
        raise

    try:
        all_services = manager.get_services()
    except CybleAuthError as e:
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] Authentication failed: {e}")
        siemplify.end(f"Authentication failed: {e}", "FAILED")
        return
    except CybleAPIError as e:
        siemplify.LOGGER.error(f"[{SCRIPT_NAME}] Failed to fetch services list: {e}")
        siemplify.end(f"Could not fetch services: {e}", "FAILED")
        return

    if not all_services:
        siemplify.LOGGER.info(f"[{SCRIPT_NAME}] [WARN] No active services. Skipping cycle.")
        siemplify.end("No services available.", "COMPLETED")
        return

    if services_filter.strip():
        allowed = {s.strip().lower() for s in services_filter.split(",") if s.strip()}
        target_services = [s for s in all_services if s["name"].lower() in allowed]
    else:
        target_services = all_services

    siemplify.LOGGER.info(
        f"[{SCRIPT_NAME}] Refreshing case fields for {len(target_services)} services."
    )

    now = datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    total_updated = 0
    total_skipped = 0
    total_not_in_soar = 0
    failed_services = []

    for service_def in target_services:
        service_name = service_def["name"]
        try:
            updated, skipped, not_in_soar = _refresh_service(
                siemplify=siemplify,
                manager=manager,
                service_name=service_name,
                now=now,
                now_iso=now_iso,
                hours_back=hours_back,
                max_per_cycle=max_per_cycle,
            )
            total_updated += updated
            total_skipped += skipped
            total_not_in_soar += not_in_soar

            # Short-circuit: if dedup lookup isn't supported on this SOAR build,
            # we can't find existing cases at all — abort the rest of the run.
            if _DEDUP_LOOKUP_AVAILABLE is False:
                siemplify.LOGGER.info(
                    f"[{SCRIPT_NAME}] Dedup lookup unsupported on this SOAR build — "
                    "drift refresh is a no-op. Use UpdateAlertStatus/Severity actions "
                    "for manual sync. Stopping cycle."
                )
                break

        except CybleAuthError as e:
            siemplify.LOGGER.error(
                f"[{SCRIPT_NAME}] Auth error on '{service_name}': {e}. Aborting job."
            )
            siemplify.end(f"Auth failure: {e}", "FAILED")
            return
        except Exception as e:  # noqa: BLE001
            siemplify.LOGGER.error(
                f"[{SCRIPT_NAME}] Failed refreshing '{service_name}': {e}",
                exc_info=True,
            )
            failed_services.append(service_name)
            continue

    summary = (
        f"Refresh complete. Cases updated: {total_updated}, "
        f"skipped (no drift): {total_skipped}, "
        f"new alerts (handled by Connector): {total_not_in_soar}."
    )
    if failed_services:
        summary += f" FAILED services: {failed_services}."

    siemplify.LOGGER.info(f"[{SCRIPT_NAME}] {summary}")
    siemplify.end(summary, "COMPLETED" if not failed_services else "COMPLETED_WITH_ERRORS")


def _refresh_service(
    siemplify,
    manager,
    service_name,
    now,
    now_iso,
    hours_back,
    max_per_cycle,
):
    """
    Refresh existing SOAR cases for one service.

    For each Cyble alert in the window:
      - If the alert exists in SOAR and Cyble's `updated_at` > our last sync,
        update the case's CybleStatus/Severity/LastSyncAt fields.
      - If the alert exists and `updated_at` is not newer, skip silently.
      - If the alert does NOT exist in SOAR, log it (Connector will pick it up)
        and count it for the summary.

    Returns (updated_count, skipped_count, not_in_soar_count).
    """
    state_key = f"{STATE_KEY_LAST_RUN_PREFIX}{service_name}"
    raw_cursor = siemplify.get_job_context_property(
        identifier=INTEGRATION_NAME,
        property_key=state_key,
    )
    if raw_cursor:
        try:
            gte = datetime.fromisoformat(raw_cursor).astimezone(timezone.utc)
        except ValueError:
            gte = now - timedelta(hours=hours_back)
    else:
        gte = now - timedelta(hours=hours_back)

    lte = now

    siemplify.LOGGER.info(
        f"[{service_name}] Refresh window {gte.isoformat()} → {lte.isoformat()}"
    )

    updated_count = 0
    skipped_count = 0
    not_in_soar_count = 0

    for batch in manager.iter_alerts(
        services=[service_name],
        gte=gte,
        lte=lte,
        max_total=max_per_cycle,
    ):
        for raw_alert in batch:
            alert_id = CybleAlertMapper.build_idempotency_key(raw_alert)
            if not alert_id:
                continue

            existing = _find_existing_alert(siemplify, alert_id)
            if existing is None:
                # Connector handles this — not our concern.
                not_in_soar_count += 1
                continue

            case_id, alert_obj = existing
            raw_updated = raw_alert.get("updated_at", "")
            last_sync = (alert_obj.get("additional_properties") or {}).get(
                FIELD_LAST_SYNC_AT, ""
            )
            if _is_newer(raw_updated, last_sync):
                _update_existing_alert(siemplify, case_id, alert_obj, raw_alert, now_iso)
                updated_count += 1
            else:
                skipped_count += 1

    siemplify.set_job_context_property(
        identifier=INTEGRATION_NAME,
        property_key=state_key,
        property_value=now_iso,
    )
    return updated_count, skipped_count, not_in_soar_count


def _find_existing_alert(
    siemplify: SiemplifyJob, cyble_alert_id: str
) -> tuple[str, dict] | None:
    """
    Look up an existing SOAR case/alert by the AlertId custom field.

    `get_cases_by_filter` returns a list of case IDs (not Case/Alert objects), so
    each ID is resolved to a full case via `_get_case_by_id`, and its
    `cyber_alerts` are scanned for the alert whose AlertId custom field matches
    `cyble_alert_id`. Returns a ``(case_id, alert_dict)`` tuple, or ``None`` if
    not found / lookup unsupported on this SOAR build.
    """
    global _DEDUP_LOOKUP_AVAILABLE

    if _DEDUP_LOOKUP_AVAILABLE is False:
        return None

    if not hasattr(siemplify, "get_cases_by_filter"):
        if _DEDUP_LOOKUP_AVAILABLE is None:
            siemplify.LOGGER.info(
                "[WARN] SiemplifyJob.get_cases_by_filter not available on this SOAR build."
            )
        _DEDUP_LOOKUP_AVAILABLE = False
        return None

    # First try with custom_fields kwarg (newer SOAR builds).
    try:
        case_ids = siemplify.get_cases_by_filter(
            custom_fields={FIELD_ALERT_ID: cyble_alert_id},
            limit=1,
        )
        _DEDUP_LOOKUP_AVAILABLE = True
    except TypeError:
        # Older build — get_cases_by_filter exists but doesn't accept custom_fields.
        # We can't filter server-side; mark unsupported and bail. Drift refresh
        # would require iterating ALL open cases per service which is unsafe at scale.
        if _DEDUP_LOOKUP_AVAILABLE is None:
            siemplify.LOGGER.info(
                "[WARN] get_cases_by_filter does not accept custom_fields on this build. "
                "Drift refresh disabled — use UpdateAlertStatus/Severity actions instead."
            )
        _DEDUP_LOOKUP_AVAILABLE = False
        return None
    except Exception as e:  # noqa: BLE001
        if _DEDUP_LOOKUP_AVAILABLE is None:
            siemplify.LOGGER.info(f"[WARN] Dedup lookup unavailable: {e}.")
        _DEDUP_LOOKUP_AVAILABLE = False
        return None

    # Resolve each matching case ID to a full case and locate the specific alert
    # carrying our AlertId custom field.
    for case_id in case_ids or []:
        try:
            case = siemplify._get_case_by_id(case_id)
        except Exception as e:  # noqa: BLE001
            siemplify.LOGGER.info(f"[WARN] Could not load case {case_id}: {e}.")
            continue
        for alert in case.get("cyber_alerts", []) or []:
            props = alert.get("additional_properties") or {}
            if props.get(FIELD_ALERT_ID) == cyble_alert_id:
                return str(case_id), alert
    return None


def _is_newer(raw_updated, last_sync):
    """Return True if raw_updated is strictly after last_sync."""
    if not raw_updated or not last_sync:
        return False
    try:
        raw_dt = datetime.fromisoformat(raw_updated).astimezone(timezone.utc)
        sync_dt = datetime.fromisoformat(last_sync).astimezone(timezone.utc)
        return raw_dt > sync_dt
    except ValueError:
        return False


def _update_existing_alert(
    siemplify: SiemplifyJob,
    case_id: str,
    alert_obj: dict,
    raw_alert: dict,
    now_iso: str,
) -> None:
    """
    Refresh Status / Severity / LastSyncAt on the existing SOAR alert and add
    a wall comment for audit. Field names are vendor-neutral (no "Cyble"
    prefix) so the same custom fields work for any customer skin.
    """
    global _UPDATE_API_AVAILABLE

    if _UPDATE_API_AVAILABLE is False:
        return

    alert_identifier = alert_obj.get("identifier")
    if not alert_identifier:
        return

    if not hasattr(siemplify, "update_alert_additional_data"):
        if _UPDATE_API_AVAILABLE is None:
            siemplify.LOGGER.info(
                "[WARN] update_alert_additional_data not available — drift refresh skipped."
            )
        _UPDATE_API_AVAILABLE = False
        return

    new_severity = (raw_alert.get("user_severity") or raw_alert.get("severity") or "LOW").upper()
    new_status = (raw_alert.get("status") or "UNREVIEWED").upper()

    try:
        siemplify.update_alert_additional_data(
            alert_id=alert_identifier,
            additional_data={
                FIELD_LAST_SYNC_AT: now_iso,
                FIELD_STATUS:       new_status,
                FIELD_SEVERITY:     new_severity,
            },
        )
        if hasattr(siemplify, "add_comment"):
            siemplify.add_comment(
                comment=(
                    f"[Sync] Alert updated upstream at {raw_alert.get('updated_at')}. "
                    f"New status: {new_status}, severity: {new_severity}."
                ),
                case_id=case_id,
                alert_identifier=alert_identifier,
            )
        _UPDATE_API_AVAILABLE = True
    except Exception as e:  # noqa: BLE001
        if _UPDATE_API_AVAILABLE is None:
            siemplify.LOGGER.info(
                f"[WARN] Could not update alert {alert_identifier}: {e}. "
                "Subsequent updates skipped."
            )
        _UPDATE_API_AVAILABLE = False


if __name__ == "__main__":
    main()
