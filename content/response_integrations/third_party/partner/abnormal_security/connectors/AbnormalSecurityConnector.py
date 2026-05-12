"""Abnormal Security Threats & Cases Connector for Google SecOps SOAR."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import CaseInfo
from soar_sdk.SiemplifyUtils import (
    convert_datetime_to_unix_time,
    convert_string_to_unix_time,
    dict_to_flat,
    output_handler,
    unix_now,
)

from ..core.AbnormalManager import (
    AbnormalAuthenticationError,
    AbnormalConnectionError,
    AbnormalManager,
    AbnormalValidationError,
)
from ..core.constants import (
    CONNECTOR_SCRIPT_NAME,
    DEFAULT_MAX_ALERTS_PER_CYCLE,
    DEFAULT_MAX_DAYS_BACKWARDS,
    DEVICE_PRODUCT_CASE,
    DEVICE_PRODUCT_THREAT,
    DEVICE_VENDOR,
    IDS_CACHE_HOURS,
)

IDS_FILE = "ids.json"

PRIORITY_MAP = {
    "CRITICAL": 100,
    "HIGH": 80,
    "MEDIUM": 60,
    "LOW": 40,
}


def _to_priority(level: str | None) -> int:
    return PRIORITY_MAP.get((level or "").upper(), -1)


def _unix_ms_from_iso(iso_str: str | None) -> int:
    if not iso_str:
        return unix_now()
    try:
        return convert_string_to_unix_time(iso_str)
    except Exception:
        return unix_now()


def _last_run_to_iso(last_run_ms: int) -> str:
    dt = datetime.fromtimestamp(last_run_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_timestamp(timestamp_ms: int, max_days_backwards: int) -> int:
    from datetime import timedelta
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max_days_backwards)
    cutoff_ms = convert_datetime_to_unix_time(cutoff)
    return max(timestamp_ms, cutoff_ms)


def _read_ids(ids_file_path: str, logger) -> dict:
    if not os.path.exists(ids_file_path):
        return {}
    try:
        with open(ids_file_path) as f:
            existing = json.loads(f.read())
        cutoff_ms = unix_now() - IDS_CACHE_HOURS * 3600 * 1000
        return {id_: ts for id_, ts in existing.items() if ts > cutoff_ms}
    except Exception as e:
        logger.error(f"Unable to read ids file: {e}")
        return {}


def _write_ids(ids_file_path: str, ids: dict, logger) -> None:
    try:
        os.makedirs(os.path.dirname(ids_file_path), exist_ok=True)
        with open(ids_file_path, "w") as f:
            f.write(json.dumps(ids))
    except Exception as e:
        logger.error(f"Unable to write ids file: {e}")


def _build_threat_case_info(threat: dict, environment: str) -> CaseInfo:
    case_info = CaseInfo()
    case_info.ticket_id = threat.get("threatId", "")
    case_info.display_id = case_info.ticket_id
    attack_type = threat.get("attackType", "Unknown")
    subject = threat.get("subject", "")
    case_info.name = f"[Threat] {attack_type}: {subject}" if subject else f"[Threat] {attack_type}"
    case_info.rule_generator = attack_type
    case_info.device_vendor = DEVICE_VENDOR
    case_info.device_product = DEVICE_PRODUCT_THREAT
    case_info.start_time = _unix_ms_from_iso(threat.get("receivedTime"))
    case_info.end_time = case_info.start_time
    case_info.priority = _to_priority(threat.get("confidence"))
    case_info.environment = environment
    case_info.events = [dict_to_flat(threat)]
    return case_info


def _build_case_case_info(case: dict, environment: str) -> CaseInfo:
    case_info = CaseInfo()
    case_info.ticket_id = str(case.get("caseId", ""))
    case_info.display_id = case_info.ticket_id
    description = case.get("description", "Abnormal Case")
    case_info.name = f"[Case] {description}"
    case_info.rule_generator = "Abnormal Case"
    case_info.device_vendor = DEVICE_VENDOR
    case_info.device_product = DEVICE_PRODUCT_CASE
    time_field = (
        case.get("firstObserved")
        or case.get("customerVisibleTime")
        or case.get("lastModifiedTime")
    )
    case_info.start_time = _unix_ms_from_iso(time_field)
    case_info.end_time = case_info.start_time
    case_info.priority = _to_priority(case.get("severity_level") or case.get("confidence"))
    case_info.environment = environment
    case_info.events = [dict_to_flat(case)]
    return case_info


@output_handler
def main(test_handler: bool = False) -> None:
    connector_scope = SiemplifyConnectorExecution()
    connector_scope.script_name = CONNECTOR_SCRIPT_NAME

    if test_handler:
        connector_scope.LOGGER.info("========== Starting Connector Test ==========")
    else:
        connector_scope.LOGGER.info("========== Starting Connector ==========")

    output_variables: dict = {}
    log_items: list = []
    cases: list = []

    try:
        api_url = connector_scope.extract_connector_param(
            "API URL", is_mandatory=True, print_value=True
        )
        api_key = connector_scope.extract_connector_param("API Key", is_mandatory=True)
        verify_ssl = connector_scope.extract_connector_param(
            "Verify SSL", input_type=bool, default_value=True
        )
        max_days_backwards = connector_scope.extract_connector_param(
            "Max Days Backwards", input_type=int, default_value=DEFAULT_MAX_DAYS_BACKWARDS
        )
        max_alerts_per_cycle = connector_scope.extract_connector_param(
            "Max Alerts Per Cycle", input_type=int, default_value=DEFAULT_MAX_ALERTS_PER_CYCLE
        )
        force_from_date = connector_scope.extract_connector_param(
            "Force From Date", default_value="None"
        )
        environment = connector_scope.context.connector_info.environment or ""

        manager = AbnormalManager(api_url=api_url, api_key=api_key, verify_ssl=verify_ssl)

        if force_from_date and force_from_date.strip().lower() not in ("", "none"):
            raw_last_run = convert_string_to_unix_time(force_from_date.strip())
            connector_scope.LOGGER.info(f"Force From Date override: {force_from_date.strip()}")
        else:
            raw_last_run = connector_scope.fetch_timestamp()
        last_run_ms = _validate_timestamp(raw_last_run, max_days_backwards)
        last_run_iso = _last_run_to_iso(last_run_ms)
        connector_scope.LOGGER.info(f"Polling for events since {last_run_iso}")

        ids_file_path = os.path.join(connector_scope.run_folder, IDS_FILE)
        existing_ids = _read_ids(ids_file_path, connector_scope.LOGGER)

        all_alerts: list[tuple[str, dict]] = []

        # --- Threats ---
        try:
            connector_scope.LOGGER.info("Fetching threats from Abnormal Security")
            threats_resp = manager.list_threats(
                filter_str=f"receivedTime gte {last_run_iso}",
                page_size=min(max_alerts_per_cycle, 100),
            )
            for threat in threats_resp.get("threats", []):
                all_alerts.append(("threat", threat))
        except (AbnormalAuthenticationError, AbnormalConnectionError, AbnormalValidationError) as e:
            connector_scope.LOGGER.error(f"Failed to fetch threats: {e}")

        # --- Cases ---
        try:
            connector_scope.LOGGER.info("Fetching cases from Abnormal Security")
            cases_resp = manager.list_cases(
                filter_str=f"createdTime gte {last_run_iso}",
                page_size=min(max_alerts_per_cycle, 100),
            )
            for case in cases_resp.get("cases", []):
                all_alerts.append(("case", case))
        except (AbnormalAuthenticationError, AbnormalConnectionError, AbnormalValidationError) as e:
            connector_scope.LOGGER.error(f"Failed to fetch cases: {e}")

        connector_scope.LOGGER.info(f"Retrieved {len(all_alerts)} total events before dedup")

        if test_handler:
            all_alerts = all_alerts[:1]

        latest_time_ms = last_run_ms

        for kind, alert in all_alerts:
            if len(cases) >= max_alerts_per_cycle:
                connector_scope.LOGGER.info(
                    f"Reached max alerts per cycle ({max_alerts_per_cycle})"
                )
                break

            if kind == "threat":
                alert_id = f"threat_{alert.get('threatId', '')}"
                time_field = alert.get("receivedTime")
            else:
                alert_id = f"case_{alert.get('caseId', '')}"
                time_field = (
                    alert.get("firstObserved")
                    or alert.get("customerVisibleTime")
                    or alert.get("last_modified")
                )

            if not alert_id or alert_id in existing_ids:
                continue

            try:
                if kind == "threat":
                    case_info = _build_threat_case_info(alert, environment)
                else:
                    case_info = _build_case_case_info(alert, environment)

                is_overflow = False
                try:
                    is_overflow = connector_scope.is_overflowed_alert(
                        environment=case_info.environment,
                        alert_identifier=str(case_info.ticket_id),
                        alert_name=str(case_info.rule_generator),
                        product=str(case_info.device_product),
                    )
                except Exception as e:
                    connector_scope.LOGGER.error(f"Overflow check failed for {alert_id}: {e}")

                if is_overflow:
                    connector_scope.LOGGER.warning(f"Overflowed on {alert_id}")
                    continue

                cases.append(case_info)
                existing_ids[alert_id] = case_info.start_time

                if time_field:
                    event_ms = _unix_ms_from_iso(time_field)
                    if event_ms > latest_time_ms:
                        latest_time_ms = event_ms

            except Exception as e:
                connector_scope.LOGGER.error(f"Failed to create CaseInfo for {alert_id}: {e}")
                connector_scope.LOGGER.exception(e)
                if test_handler:
                    raise

        connector_scope.LOGGER.info(f"Returning {len(cases)} cases to SOAR")

        if not test_handler:
            try:
                connector_scope.save_timestamp(new_timestamp=latest_time_ms)
                _write_ids(ids_file_path, existing_ids, connector_scope.LOGGER)
            except Exception as e:
                connector_scope.LOGGER.error(f"Unable to save state: {e}")

        connector_scope.return_package(cases, output_variables, log_items)

    except Exception as e:
        connector_scope.LOGGER.error(str(e))
        connector_scope.LOGGER.exception(e)
        if test_handler:
            raise


if __name__ == "__main__":
    # SOAR platform passes "False" for test runs, "True" for production
    main(test_handler=(len(sys.argv) >= 2 and sys.argv[1] == "False"))
