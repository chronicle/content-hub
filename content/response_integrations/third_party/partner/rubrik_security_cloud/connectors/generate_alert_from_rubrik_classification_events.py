from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.utils import is_overflowed

from ..core.api_manager import APIManager
from ..core.constants import (
    CHECKPOINT_FILE_NAME,
    CLASSIFICATION_ACTIVITY_MESSAGE_FILTER,
    CLASSIFICATION_CONNECTOR_NAME,
    CLASSIFICATION_CONNECTOR_VERSION,
    EVENTS_PAGE_SIZE,
    MAX_SEARCH_TIME_PERIOD_DAYS,
    MIN_SEARCH_TIME_PERIOD_DAYS,
)
from ..core.datamodels import RubrikClassificationAlertDatamodel

connector_starting_time = unix_now()

TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


def validate_search_time_period(days):
    """Validate 'Search Time Period In Days': must be a whole number within bounds."""
    if days is None or str(days).strip() == "":
        return MIN_SEARCH_TIME_PERIOD_DAYS
    try:
        days = int(str(days).strip())
    except (TypeError, ValueError):
        raise ValueError(
            f"'Search Time Period In Days' must be a whole number. Received: {days}."
        )
    if days > MAX_SEARCH_TIME_PERIOD_DAYS:
        raise ValueError(
            f"'Search Time Period In Days' cannot exceed {MAX_SEARCH_TIME_PERIOD_DAYS} days. "
            f"Received: {days}."
        )
    if days < MIN_SEARCH_TIME_PERIOD_DAYS:
        raise ValueError(
            f"'Search Time Period In Days' cannot be negative. Received: {days}."
        )
    return days


def _get_checkpoint_path(siemplify):
    """Resolve the persistent checkpoint file path inside the connector run folder."""
    folder = getattr(siemplify, "run_folder", None) or os.getcwd()
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
    except Exception:
        folder = os.getcwd()
    return os.path.join(folder, CHECKPOINT_FILE_NAME)


def read_checkpoint(siemplify):
    """Read the {from_timestamp} checkpoint. Returns {} if absent."""
    path = _get_checkpoint_path(siemplify)
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle) or {}
    except Exception as err:
        siemplify.LOGGER.error(f"Failed to read checkpoint from {path}: {err}")
    return {}


def write_checkpoint(siemplify, from_timestamp):
    """Persist the from_timestamp the next run should start from."""
    path = _get_checkpoint_path(siemplify)
    data = {"from_timestamp": from_timestamp}
    try:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        siemplify.LOGGER.info(f"Checkpoint updated: from_timestamp set to '{from_timestamp}'.")
    except Exception as err:
        siemplify.LOGGER.error(f"Failed to write checkpoint to {path}: {err}")


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CLASSIFICATION_CONNECTOR_NAME
    siemplify.LOGGER.info(f"Classification connector version: {CLASSIFICATION_CONNECTOR_VERSION}")

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")

    service_account_json = extract_connector_param(
        siemplify,
        param_name="Service Account JSON",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=False,
        print_value=True,
    )

    search_time_period_days = extract_connector_param(
        siemplify,
        param_name="Search Time Period In Days",
        default_value="1",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=False,
    )

    # Backed by the built-in "Event Field Name" UI field (param name: EventClassId).
    event_field_parameter = extract_connector_param(
        siemplify,
        param_name="EventClassId",
        input_type=str,
        is_mandatory=False,
        default_value="eventName",
        print_value=True,
    )

    # Backed by the built-in "Product Field Name" UI field (param name: DeviceProductField).
    product_field_name = extract_connector_param(
        siemplify,
        param_name="DeviceProductField",
        input_type=str,
        is_mandatory=False,
        default_value="Rubrik Security Cloud",
        print_value=True,
    )

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    alerts = []

    try:
        # Validate the search window (must not exceed 1 day).
        search_time_period_days = validate_search_time_period(search_time_period_days)

        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.strftime(TIME_FORMAT)
        default_start_iso = (now_dt - timedelta(days=search_time_period_days)).strftime(TIME_FORMAT)

        manager = APIManager(
            service_account_json=service_account_json,
            verify_ssl=verify_ssl,
            siemplify=siemplify,
        )

        # ----------------------------------------------------------------
        # Time window. from_timestamp comes from the checkpoint (last run's
        # window end) or falls back to now - search period on the first run.
        # to_timestamp is always now.
        # ----------------------------------------------------------------
        checkpoint = {} if is_test_run else read_checkpoint(siemplify)
        checkpoint_from = checkpoint.get("from_timestamp")
        if checkpoint_from:
            siemplify.LOGGER.info(f"Fetched from_timestamp '{checkpoint_from}' from checkpoint.")
        else:
            siemplify.LOGGER.info(
                "No from_timestamp found in checkpoint; "
                f"defaulting to '{default_start_iso}' (now - {search_time_period_days} day)."
            )
        from_iso = checkpoint_from or default_start_iso
        to_iso = now_iso

        siemplify.LOGGER.info(f"Fetching classification events from {from_iso} to {to_iso}.")

        # ----------------------------------------------------------------
        # Step 1: Fetch every page of CLASSIFICATION/SUCCESS events for the
        #         window in a single pass (walk all cursors).
        # ----------------------------------------------------------------
        all_edges = []
        next_page_token = None
        has_next_page = True

        while has_next_page:
            response = manager.list_events(
                activity_types=["CLASSIFICATION"],
                activity_statuses=["SUCCESS"],
                start_date=from_iso,
                end_date=to_iso,
                sort_order="ASC",
                limit=EVENTS_PAGE_SIZE,
                next_page_token=next_page_token,
            )

            connection = response.get("data", {}).get("activitySeriesConnection", {})
            edges = connection.get("edges", [])
            all_edges.extend(edges)

            page_info = connection.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            next_page_token = page_info.get("endCursor")

            siemplify.LOGGER.info(
                f"Page fetched: {len(edges)} events (running total: {len(all_edges)})."
            )

            if not next_page_token:
                break

        # ----------------------------------------------------------------
        # Step 2 + 3: Filter by classification message, then dedup by
        #             objectId keeping the latest-lastUpdated entry.
        # ----------------------------------------------------------------
        latest_per_object = {}

        for edge in all_edges:
            node = edge.get("node", {})
            object_id = node.get("objectId", "")

            # Skip null / system-level objectIds
            if not object_id or object_id == "00000000-0000-0000-0000-000000000000":
                continue

            # Filter: only keep nodes that contain the "Results available" message
            activity_nodes = node.get("activityConnection", {}).get("nodes", [])
            has_results_node = any(
                CLASSIFICATION_ACTIVITY_MESSAGE_FILTER in n.get("message", "")
                for n in activity_nodes
            )
            if not has_results_node:
                continue

            # Dedup: keep the node with the highest lastUpdated per objectId
            last_updated = node.get("lastUpdated", "")
            existing = latest_per_object.get(object_id)
            if existing is None or last_updated > existing.get("lastUpdated", ""):
                latest_per_object[object_id] = node

        siemplify.LOGGER.info(
            f"Fetched {len(all_edges)} events; {len(latest_per_object)} unique objects "
            "after filter + dedup."
        )

        environment_common = GetEnvironmentCommonFactory.create_environment_manager(
            siemplify,
            "",
            "",
        )

        # ----------------------------------------------------------------
        # Steps 4-5: For each deduplicated object, resolve snapshot ->
        #            fetch policyObj -> check violations -> build alert.
        # ----------------------------------------------------------------
        for event_node in latest_per_object.values():
            activity_series_id = event_node.get("activitySeriesId") or event_node.get("id", "")
            object_id = event_node.get("objectId", "")
            last_updated = event_node.get("lastUpdated", "")

            siemplify.LOGGER.info(
                f"Processing event: {activity_series_id} "
                f"(object: {event_node.get('objectName') or object_id})"
            )

            try:
                # Step 4: Resolve closest snapshot before lastUpdated
                snapshot_id = None
                snapshot_date = None
                if object_id and last_updated:
                    try:
                        snap_response = manager.get_closest_snapshot(
                            snappable_id=object_id,
                            before_time=last_updated,
                        )
                        snap_list = snap_response.get("data", {}).get(
                            "allSnapshotsClosestToPointInTime", []
                        )
                        for snap_entry in snap_list:
                            error = snap_entry.get("error")
                            if error:
                                siemplify.LOGGER.error(
                                    f"Snapshot API error for {object_id}: {error}"
                                )
                                break
                            snap = snap_entry.get("snapshot")
                            if snap:
                                snapshot_id = snap.get("id")
                                snapshot_date = snap.get("date")
                            break
                    except Exception as snap_err:
                        siemplify.LOGGER.error(
                            f"Could not resolve snapshot for {object_id}: {snap_err}"
                        )

                if not snapshot_id:
                    siemplify.LOGGER.info(
                        f"Skipping {activity_series_id}: no snapshot for {object_id}."
                    )
                    continue

                siemplify.LOGGER.info(f"Snapshot resolved: {snapshot_id} (date: {snapshot_date}).")

                # Step 5: Fetch policyObj and check violations
                policy_obj = {}
                try:
                    pol_response = manager.get_classification_object_detail(
                        snappable_fid=object_id,
                        snapshot_fid=snapshot_id,
                    )
                    policy_obj = pol_response.get("data", {}).get("policyObj") or {}
                except Exception as pol_err:
                    siemplify.LOGGER.error(
                        f"Could not retrieve policyObj for {object_id}/{snapshot_id}: {pol_err}"
                    )

                if not policy_obj:
                    siemplify.LOGGER.info(f"Skipping {activity_series_id}: no policyObj data.")
                    continue

                violations = (
                    policy_obj.get("rootFileResult", {}).get("hits", {}).get("violations", 0)
                )

                siemplify.LOGGER.info(
                    f"Checking violation count for object {object_id}: violations={violations}."
                )
                if violations > 0:
                    siemplify.LOGGER.info(
                        f"Object {object_id} has violations > 0; proceeding to build alert."
                    )
                else:
                    siemplify.LOGGER.info(
                        f"Object {object_id} has no violations (count not greater than 0). "
                        f"Skipping {activity_series_id}."
                    )
                    continue

                # Build AlertInfo
                classification_event = RubrikClassificationAlertDatamodel(
                    event_node, policy_obj, snapshot_id
                )

                alert_info = classification_event.get_alert_info(
                    AlertInfo(),
                    environment_common,
                    event_field_parameter,
                    product_field_name,
                )

                if is_overflowed(siemplify, alert_info, is_test_run):
                    siemplify.LOGGER.info(
                        f"{alert_info.rule_generator}-{alert_info.ticket_id}"
                        f"-{alert_info.environment}-{alert_info.device_product}"
                        " found as overflow alert. Skipping."
                    )
                    continue

                alerts.append(alert_info)
                siemplify.LOGGER.info(
                    f"Alert added: {alert_info.ticket_id} "
                    f"({violations} violations, riskLevel={policy_obj.get('riskLevel')})"
                )

            except Exception as e:
                siemplify.LOGGER.error(f"Failed to process event {activity_series_id}. Error: {e}")
                siemplify.LOGGER.exception(e)
                if is_test_run:
                    raise

        # ----------------------------------------------------------------
        # Step 6: All alerts gathered. Ingest only if we are not approaching
        #         the process timeout; otherwise exit gracefully without
        #         ingesting or advancing the checkpoint so the next run redoes
        #         this window.
        # ----------------------------------------------------------------
        # NOTE: return_package finalizes and flushes the connector output, so
        # any logging or checkpoint write MUST happen before it — otherwise
        # those log lines never reach the debug output.
        if is_approaching_timeout(connector_starting_time, python_process_timeout):
            siemplify.LOGGER.info(
                "Timeout is approaching. Exiting gracefully without ingesting; "
                "checkpoint unchanged."
            )
            package = []
        else:
            siemplify.LOGGER.info(f"Ingesting {len(alerts)} alerts.")
            if not is_test_run:
                write_checkpoint(siemplify, to_iso)
            package = alerts

        siemplify.LOGGER.info("------------------- Main - Finished -------------------")
        siemplify.return_package(package)

    except Exception as e:
        siemplify.LOGGER.error(f"Got exception on main handler. Error: {e}")
        siemplify.LOGGER.exception(e)
        if is_test_run:
            raise
        # On a scheduled run, always hand the framework a valid (empty) package
        # so a failure exits gracefully instead of returning null output
        # (which surfaces as a JSON deserialization ArgumentNullException).
        siemplify.return_package([])


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
