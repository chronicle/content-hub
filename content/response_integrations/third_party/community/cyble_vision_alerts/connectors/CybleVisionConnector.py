"""
CybleVisionConnector — scheduled SOAR connector that ingests Cyble Vision alerts as cases.

Why a connector (not a job):
  - SOAR's Job SDK does not expose case-creation APIs; only connectors can emit
    AlertInfo objects which SOAR turns into cases.
  - This connector polls Cyble at the configured interval, builds AlertInfo
    objects from each alert via CybleAlertMapper, and returns them via
    siemplify.return_package(...).

Workflow per run:
  1. Resolve the active services list from Cyble (or use the configured filter).
  2. For each service, determine the fetch window using a per-service cursor
     stored in the connector context. First-run cursor is now - HOURS_BACK.
  3. Paginate alerts; each alert becomes one AlertInfo with one event payload.
  4. Append AlertInfos to the run's list; advance the cursor only after the
     service's pagination completes successfully.
  5. siemplify.return_package(alerts) — SOAR creates cases.

Deduplication:
  - SOAR de-duplicates by AlertInfo.display_id natively. We use the Cyble alert
    UUID (immutable) as display_id so re-fetched alerts never produce duplicates.
  - In-place updates to existing cases (severity/status drift in Cyble) are
    handled by SyncAlertsJob, not this connector.
"""
from __future__ import annotations

import sys
import json
from datetime import datetime, timezone, timedelta

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler

from ..core.CybleManager import CybleManager, CybleAPIError, CybleAuthError
from ..core.CybleAlertMapper import CybleAlertMapper
from ..core.constants import (
    INTEGRATION_NAME,
    PARAM_API_KEY,
    PARAM_BASE_URL,
    PARAM_VERIFY_SSL,
    PARAM_TIMEOUT,
    PARAM_MAX_PER_CYCLE,
    PARAM_SERVICES,
    PARAM_HOURS_BACK,
    DEFAULT_MAX_PER_CYCLE,
    DEFAULT_HOURS_BACK,
    DEFAULT_TIMEOUT,
    DEFAULT_BASE_URL,
    STATE_KEY_LAST_RUN_PREFIX,
    FIELD_ALERT_ID,
    FIELD_SERVICE,
    FIELD_LAST_SYNC_AT,
    HIGH_PRIORITY_SERVICES,
)

CONNECTOR_NAME = "Cyble Vision Alerts Connector"
VENDOR  = "Cyble"
PRODUCT = "Cyble Vision Alerts"


# Map our SecOps severity ints → connector AlertInfo.priority scale.
# (SecOps SOAR uses a different priority scale for AlertInfo than for cases.)
#   SecOps int  →  AlertInfo.priority
#       -1 (CRITICAL) →  100
#        2 (HIGH)     →   80
#        1 (MEDIUM)   →   60
#        0 (LOW)      →   40
_SECOPS_SEVERITY_TO_PRIORITY = {
    -1: 100,
     2:  80,
     1:  60,
     0:  40,
}


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME

    if is_test_run:
        siemplify.LOGGER.info(
            "[CybleVisionConnector] This is a TEST RUN (IDE Play button). "
            "Cursors will not be advanced."
        )

    # ── Parameters ────────────────────────────────────────────────────────────
    api_key  = siemplify.extract_connector_param(param_name=PARAM_API_KEY,    is_mandatory=True)
    base_url = siemplify.extract_connector_param(param_name=PARAM_BASE_URL,   default_value=DEFAULT_BASE_URL)
    verify_ssl = siemplify.extract_connector_param(
        param_name=PARAM_VERIFY_SSL, input_type=bool, default_value=True
    )
    timeout = siemplify.extract_connector_param(
        param_name=PARAM_TIMEOUT, input_type=int, default_value=DEFAULT_TIMEOUT
    )
    max_per_cycle = siemplify.extract_connector_param(
        param_name=PARAM_MAX_PER_CYCLE, input_type=int, default_value=DEFAULT_MAX_PER_CYCLE
    )
    hours_back = siemplify.extract_connector_param(
        param_name=PARAM_HOURS_BACK, input_type=int, default_value=DEFAULT_HOURS_BACK
    )
    services_filter = siemplify.extract_connector_param(
        param_name=PARAM_SERVICES, default_value=""
    ) or ""

    siemplify.LOGGER.info("[CybleVisionConnector] Connector started.")

    try:
        manager = CybleManager(
            api_key=api_key,
            base_url=base_url,
            verify_ssl=verify_ssl,
            timeout=timeout,
        )
    except CybleAuthError as e:
        siemplify.LOGGER.error(f"[CybleVisionConnector] Auth configuration error: {e}")
        siemplify.return_package([])
        return

    # ── Resolve target services ───────────────────────────────────────────────
    try:
        all_services = manager.get_services()
    except CybleAuthError as e:
        siemplify.LOGGER.error(f"[CybleVisionConnector] Authentication failed fetching services: {e}")
        siemplify.return_package([])
        return
    except CybleAPIError as e:
        siemplify.LOGGER.error(f"[CybleVisionConnector] Failed to fetch services list: {e}")
        siemplify.return_package([])
        return

    if not all_services:
        siemplify.LOGGER.info("[CybleVisionConnector] [WARN] No active services. Nothing to do.")
        siemplify.return_package([])
        return

    if services_filter.strip():
        allowed = {s.strip().lower() for s in services_filter.split(",") if s.strip()}
        target_services = [s for s in all_services if s["name"].lower() in allowed]
    else:
        target_services = all_services

    siemplify.LOGGER.info(
        f"[CybleVisionConnector] Polling {len(target_services)} services: "
        f"{[s['name'] for s in target_services]}"
    )

    now = datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    all_alerts = []
    total_emitted = 0
    failed_services = []

    # ── Per-service polling ───────────────────────────────────────────────────
    for service_def in target_services:
        service_name = service_def["name"]
        try:
            emitted = _poll_service(
                siemplify=siemplify,
                manager=manager,
                service_name=service_name,
                now=now,
                now_iso=now_iso,
                hours_back=hours_back,
                max_per_cycle=max_per_cycle,
                output_alerts=all_alerts,
                is_test_run=is_test_run,
            )
            total_emitted += emitted
        except CybleAuthError as e:
            siemplify.LOGGER.error(
                f"[CybleVisionConnector] Auth error on '{service_name}': {e}. Aborting run."
            )
            siemplify.return_package(all_alerts)
            return
        except Exception as e:  # noqa: BLE001
            siemplify.LOGGER.error(
                f"[CybleVisionConnector] Failed polling '{service_name}': {e}",
                exc_info=True,
            )
            failed_services.append(service_name)
            continue

    summary = (
        f"[CybleVisionConnector] Run complete. Alerts emitted: {total_emitted}. "
        f"Services polled: {len(target_services)}."
    )
    if failed_services:
        summary += f" Failed services (will retry next cycle): {failed_services}."
    siemplify.LOGGER.info(summary)

    siemplify.return_package(all_alerts)


def _poll_service(
    siemplify,
    manager,
    service_name,
    now,
    now_iso,
    hours_back,
    max_per_cycle,
    output_alerts,
    is_test_run,
):
    """
    Poll one Cyble service and append AlertInfo objects to output_alerts.
    Returns the number of alerts appended.

    Cursor: stored as `cyble_last_run_<service>` in connector context.
    Advanced only AFTER successful pagination completes (and only when not in
    test mode), so a mid-run failure causes safe re-fetch on the next cycle.

    Cursor advancement rule (data-loss-free guarantee):
      - We fetch ASCENDING by created_at, so each batch goes oldest → newest.
      - We track the maximum created_at across all alerts successfully
        processed in this run, and advance the cursor to THAT timestamp —
        not to `now`.
      - If max_per_cycle truncates a high-volume window, the slice we drop
        is the *newest* portion of the window. The next cycle resumes from
        the last-processed timestamp and naturally picks up that tail.
      - Dedup via display_id (the Cyble alert UUID) absorbs the inevitable
        single-alert boundary re-fetch at gte=max_processed_created_at.
      - If no alerts were processed (empty window), advance to now_iso so
        we don't repeatedly query a stale empty range.
    """
    state_key = f"{STATE_KEY_LAST_RUN_PREFIX}{service_name}"
    raw_cursor = _get_context(siemplify, state_key)

    if raw_cursor:
        try:
            gte = datetime.fromisoformat(raw_cursor).astimezone(timezone.utc)
        except ValueError:
            siemplify.LOGGER.info(
                f"[{service_name}] [WARN] Invalid cursor '{raw_cursor}', "
                f"resetting to {hours_back}h back."
            )
            gte = now - timedelta(hours=hours_back)
    else:
        gte = now - timedelta(hours=hours_back)
    lte = now

    siemplify.LOGGER.info(
        f"[{service_name}] Fetching alerts from {gte.isoformat()} to {lte.isoformat()}"
    )

    emitted_for_service = 0
    page_num = 0
    max_processed_dt = None  # Tracks max(created_at) of every alert we successfully process.

    for batch in manager.iter_alerts(
        services=[service_name],
        gte=gte,
        lte=lte,
        max_total=max_per_cycle,
    ):
        page_num += 1
        siemplify.LOGGER.info(
            f"[{service_name}] Processing page {page_num} ({len(batch)} alerts)"
        )

        for raw_alert in batch:
            alert_id = CybleAlertMapper.build_idempotency_key(raw_alert)
            if not alert_id:
                siemplify.LOGGER.info(
                    f"[{service_name}] [WARN] Alert missing id/data_id — skipping: {raw_alert}"
                )
                continue

            mapped = CybleAlertMapper.cyble_to_secops_alert(raw_alert, now_iso)
            alert_info = _build_alert_info(mapped, raw_alert, service_name)
            output_alerts.append(alert_info)
            emitted_for_service += 1

            # Track the newest created_at we've seen. Defensive parse —
            # an alert with a missing/malformed created_at is still emitted
            # but skipped here so it can't poison the cursor advance.
            raw_created_at = raw_alert.get("created_at")
            if raw_created_at:
                try:
                    dt = datetime.fromisoformat(raw_created_at).astimezone(timezone.utc)
                    if max_processed_dt is None or dt > max_processed_dt:
                        max_processed_dt = dt
                except (ValueError, TypeError):
                    pass

    # Decide the new cursor.
    #   - Any alert processed → advance to max(created_at) of what we processed.
    #     This is the data-loss-free advance: next cycle resumes precisely from
    #     where we left off, regardless of whether max_per_cycle truncated us.
    #   - Nothing processed (empty window or all alerts had bad created_at)
    #     → advance to now_iso so we don't keep re-scanning a stale range.
    if max_processed_dt is not None:
        new_cursor = max_processed_dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        cursor_reason = (
            f"max(created_at) of {emitted_for_service} processed alerts"
        )
    else:
        new_cursor = now_iso
        cursor_reason = "no alerts processed (advancing to now)"

    if not is_test_run:
        _set_context(siemplify, state_key, new_cursor)
        siemplify.LOGGER.info(
            f"[{service_name}] Done. Emitted={emitted_for_service}. "
            f"Cursor advanced to {new_cursor} ({cursor_reason})."
        )
    else:
        siemplify.LOGGER.info(
            f"[{service_name}] Done. Emitted={emitted_for_service}. "
            f"(test run — cursor NOT advanced; would have been {new_cursor})"
        )

    return emitted_for_service


def _build_alert_info(mapped, raw_alert, service_name):
    """
    Convert a mapped Cyble alert dict (from CybleAlertMapper) into an AlertInfo
    object that SOAR can ingest.

    Mapping notes:
      - display_id = ticket_id = Cyble alert UUID (mapped["extensions"]["AlertId"])
        SOAR uses display_id for native dedup — same UUID = same case.
      - priority comes from our SecOps severity int via _SECOPS_SEVERITY_TO_PRIORITY.
      - events[] gets the flattened raw alert + custom field extensions, so the
        playbook can read all Cyble fields without an extra GetAlerts call.
    """
    extensions = mapped.get("extensions", {})
    cyble_alert_id = extensions.get(FIELD_ALERT_ID, "")

    alert_info = AlertInfo()
    alert_info.display_id    = cyble_alert_id
    alert_info.ticket_id     = cyble_alert_id
    alert_info.name          = mapped.get("name", f"Cyble {service_name} alert")
    alert_info.rule_generator = mapped.get("rule_generator", f"Cyble Vision Alerts - {service_name}")
    alert_info.start_time    = mapped.get("start_time") or 0
    alert_info.end_time      = mapped.get("end_time") or alert_info.start_time
    alert_info.priority      = _SECOPS_SEVERITY_TO_PRIORITY.get(mapped.get("severity", 0), 40)
    alert_info.device_vendor = VENDOR
    alert_info.device_product = PRODUCT
    alert_info.environment   = "Default Environment"

    # SecOps SOAR's UI labels `priority` as "Severity" in the alert details panel.
    # Risk Score is a separate, optional float; populate from Cyble's `risk_score`
    # when present so the "Risk Score" column stops showing N/A. Set defensively —
    # older AlertInfo schemas may not have this attribute.
    raw_risk = raw_alert.get("risk_score")
    if raw_risk is not None:
        try:
            alert_info.risk_score = float(raw_risk)
        except (TypeError, ValueError):
            pass  # leave the attribute alone — non-numeric risk score from Cyble

    # Build a single flat event with all Cyble fields. SOAR's case wall renders
    # these as the alert's event details for analysts.
    event = {
        "StartTime":        alert_info.start_time,
        "EndTime":          alert_info.end_time,
        "event_name":       mapped.get("name", "Cyble Alert"),
        "device_vendor":    VENDOR,
        "device_product":   PRODUCT,
        "device_event_class_id": service_name,
        "service":          service_name,
        FIELD_ALERT_ID:    cyble_alert_id,
        FIELD_SERVICE:     service_name,
        FIELD_LAST_SYNC_AT: extensions.get(FIELD_LAST_SYNC_AT, ""),
        "high_priority_service": str(service_name in HIGH_PRIORITY_SERVICES),
    }
    # Pour the rest of the Cyble custom fields onto the event so playbook
    # filters can match against them without an enrichment step.
    for k, v in extensions.items():
        if k not in event:
            event[k] = v
    # Stash the full raw alert as a JSON blob for analyst reference.
    # Capped at 24_000 chars — SecOps enforces a hard 25_000-char limit per event
    # field value (see service-limits docs). Truncation suffix makes it obvious
    # to the analyst that the blob was cut.
    _MAX_EVENT_FIELD = 24_000
    try:
        blob = json.dumps(raw_alert, default=str)
        if len(blob) > _MAX_EVENT_FIELD:
            blob = blob[:_MAX_EVENT_FIELD] + '..."<TRUNCATED>"}'
        event["raw_alert_json"] = blob
    except Exception:  # noqa: BLE001
        event["raw_alert_json"] = ""

    alert_info.events = [event]
    alert_info.extensions = extensions

    return alert_info


# ── Context property helpers (graceful degradation across SOAR builds) ────────
# Different SOAR builds expose the connector context API differently. We probe
# for common method names and silently no-op if none are available — in that
# case the connector falls back to a fresh `hours_back` window every run, and
# SOAR's display_id dedup prevents duplicate cases.

def _get_context(siemplify, key):
    for method in ("get_connector_context_property", "get_context_property"):
        fn = getattr(siemplify, method, None)
        if callable(fn):
            try:
                return fn(identifier=INTEGRATION_NAME, property_key=key)
            except TypeError:
                try:
                    return fn(INTEGRATION_NAME, key)
                except Exception:  # noqa: BLE001
                    return None
            except Exception:  # noqa: BLE001
                return None
    return None


def _set_context(siemplify, key, value):
    for method in ("set_connector_context_property", "set_context_property"):
        fn = getattr(siemplify, method, None)
        if callable(fn):
            try:
                fn(identifier=INTEGRATION_NAME, property_key=key, property_value=value)
                return
            except TypeError:
                try:
                    fn(INTEGRATION_NAME, key, value)
                    return
                except Exception:  # noqa: BLE001
                    return
            except Exception:  # noqa: BLE001
                return


if __name__ == "__main__":
    # Connectors run in iterations. The interval is configurable in the
    # Connectors UI. The runtime passes "True" as argv[1] for a real scheduled
    # run, anything else = IDE test run.
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
