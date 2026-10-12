from __future__ import annotations

import json
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
    ACTIVITY_STATUS_SUCCESS,
    ACTIVITY_SWEEP_SORT_ORDER,
    ACTIVITY_TYPE_TO_FETCH_TYPE,
    ALL_IR_POLICY_TYPES,
    CLASSIFICATION_ACTIVITY_MESSAGE_FILTER,
    CONNECTOR_NAME,
    CONNECTOR_VERSION,
    ERROR_NO_RSC_FETCH_TYPES,
    ERROR_SERVICE_ACCOUNT_MISSING_KEYS,
    EVENTS_PAGE_SIZE,
    MAX_SEARCH_TIME_PERIOD_DAYS,
    MIN_SEARCH_TIME_PERIOD_DAYS,
    RSC_FETCH_TYPE_ACTIVITY_TYPES,
    RSC_FETCH_TYPE_CLASSIFICATION,
    RSC_FETCH_TYPE_DSPM,
    RSC_FETCH_TYPE_ENUM_MAP,
    RSC_FETCH_TYPE_IR,
    SERVICE_ACCOUNT_REQUIRED_KEYS,
)
from ..core.datamodels import (
    RubrikActivityViolationAlertDatamodel,
    RubrikClassificationAlertDatamodel,
)
from ..core.utils import string_to_multi_select, validate_json

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


def validate_service_account_json(raw_value):
    """Validate 'Service Account JSON': a JSON object carrying RSC credentials.

    Checked before any other work so a malformed or partial credential fails with
    a message naming the parameter, rather than surfacing later as a connection
    error from the API layer.

    Returns:
        The raw value, unchanged, ready to hand to APIManager.

    Raises:
        ValueError: If the value is not valid JSON or omits a required field.
    """
    service_account = validate_json(raw_value, "Service Account JSON", is_mandatory=True)
    missing = [key for key in SERVICE_ACCOUNT_REQUIRED_KEYS if not service_account.get(key)]
    if missing:
        raise ValueError(ERROR_SERVICE_ACCOUNT_MISSING_KEYS.format(", ".join(missing)))
    return raw_value


def _checkpoint_identity(siemplify):
    """(context_type, identifier) addressing this connector's server-side context.

    context_type 4 is SiemplifyConnectorExecution.CONTEXT_TYPE; the identifier is
    the connector instance's own id, so two instances of this connector keep
    independent checkpoints.
    """
    return (
        getattr(siemplify, "CONTEXT_TYPE", 4),
        siemplify.context.connector_info.identifier,
    )


def read_checkpoint(siemplify):
    """Read the {from_timestamp} checkpoint. Returns {} if none has been saved.

    Held in the SOAR server's context store, NOT on disk. A Remote connector runs
    in a fresh pod with a clean filesystem, so anything written locally is gone by
    the next run: the window is re-swept every time, the same alerts are re-emitted
    and overflow protection trips.

    get_context_property_from_server is used in preference to the plain
    get_context_property / fetch_timestamp wrappers because those branch on the
    deployment mode:

        if (not is_remote_publisher_sdk) or is_locally_scheduled_remote_connector:
            -> server DB
        else:
            -> <RUN_FOLDER>/context_file.json      # still the pod's local disk

    A remote agent connector that is not locally scheduled takes that second path,
    which is the very failure being fixed. The *_from_server / *_in_server variants
    skip the branch and always talk to the server, so one code path is correct in
    all three deployment modes.

    Falls back to the branching wrapper if the direct server call fails, so a mode
    where the session cannot reach the API degrades to today's behaviour instead of
    failing the run outright -- logged as an error, because that degraded state
    silently re-ingests.
    """
    context_type, identifier = _checkpoint_identity(siemplify)
    try:
        raw = siemplify.get_context_property_from_server(
            context_type, identifier, siemplify.TIMESTAMP_KEY
        )
    except Exception as err:
        siemplify.LOGGER.error(
            f"Could not read the checkpoint from the server context store ({err}). "
            "Falling back to the SDK's mode-dependent store, which on a Remote "
            "agent is pod-local and will cause the window to be re-ingested."
        )
        raw = None
        try:
            raw = siemplify.fetch_timestamp() or None
        except Exception as fallback_err:
            siemplify.LOGGER.error(f"Fallback checkpoint read also failed: {fallback_err}")

    last_run_unix_ms = _coerce_unix_ms(raw)
    if not last_run_unix_ms:
        return {}

    from_timestamp = datetime.fromtimestamp(
        last_run_unix_ms / 1000, tz=timezone.utc
    ).strftime(TIME_FORMAT)
    return {"from_timestamp": from_timestamp}


def _coerce_unix_ms(raw):
    """Normalise whatever the context store returns into unix milliseconds.

    The value is written with json.dumps, so it comes back as the string "1756…"
    rather than an int, and a 204 from the server surfaces as None. Anything
    unparseable is treated as "no checkpoint" rather than raising, since a corrupt
    value should cost one re-swept window, not every subsequent run.
    """
    if raw in (None, "", 0):
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        pass
    try:
        return int(json.loads(raw))
    except Exception:
        return 0


def write_checkpoint(siemplify, from_timestamp):
    """Persist the from_timestamp the next run should start from.

    Written straight to the server context store for the reason set out in
    read_checkpoint. Encoded with json.dumps to match what the SDK's own
    save_timestamp writes, so the two remain interchangeable.
    """
    parsed = datetime.strptime(from_timestamp, TIME_FORMAT).replace(tzinfo=timezone.utc)
    unix_ms = int(parsed.timestamp() * 1000)
    context_type, identifier = _checkpoint_identity(siemplify)

    try:
        siemplify.set_context_property_in_server(
            context_type, identifier, siemplify.TIMESTAMP_KEY, json.dumps(unix_ms)
        )
    except Exception as err:
        siemplify.LOGGER.error(
            f"Could not write the checkpoint to the server context store ({err}). "
            "Falling back to the SDK's mode-dependent store."
        )
        siemplify.save_timestamp(new_timestamp=unix_ms)

    siemplify.LOGGER.info(f"Checkpoint updated: from_timestamp set to '{from_timestamp}'.")


def extract_multi_select_param(siemplify, param_name, enum_map, default_value=None):
    """Extract a multi-select connector parameter and map its labels to API enums.

    Connector parameters have no dropdown type, so the values arrive as a
    comma-separated (or JSON array) string of the labels documented in the
    parameter description. string_to_multi_select handles both forms and rejects
    unknown labels.

    Returns:
        List of mapped API enum values, or None when the parameter is empty.
    """
    raw = extract_connector_param(
        siemplify,
        param_name=param_name,
        input_type=str,
        is_mandatory=False,
        default_value=default_value,
        print_value=True,
    )
    return string_to_multi_select(raw, enum_map, param_name)


def build_alert_info(
    siemplify,
    datamodel,
    environment_common,
    event_field_parameter,
    product_field_name,
    is_test_run,
):
    """Build an AlertInfo from a datamodel, returning None if it overflows."""
    alert_info = datamodel.get_alert_info(
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
        return None

    return alert_info


def fetch_activity_series(siemplify, manager, activity_types, from_iso, to_iso):
    """Walk every page of activitySeriesConnection for the selected activity types.

    All three fetch types come from this one endpoint, so they are fetched in a
    single paginated sweep and routed afterwards rather than queried separately --
    one pass over the window instead of one per fetch type.

    Args:
        siemplify: Connector execution instance, used for logging.
        manager: APIManager instance.
        activity_types: lastActivityType values to filter on, already unioned
            across the selected fetch types.
        from_iso: Window start (lastUpdatedTimeGt).
        to_iso: Window end (lastUpdatedTimeLt).

    Returns:
        List of activitySeriesConnection nodes across every page.
    """
    siemplify.LOGGER.info(
        f"Fetching activity series {activity_types} from {from_iso} to {to_iso}."
    )

    nodes = []
    next_page_token = None

    while True:
        response = manager.list_events(
            activity_types=activity_types,
            activity_statuses=[ACTIVITY_STATUS_SUCCESS],
            start_date=from_iso,
            end_date=to_iso,
            sort_order=ACTIVITY_SWEEP_SORT_ORDER,
            limit=EVENTS_PAGE_SIZE,
            next_page_token=next_page_token,
        )

        connection = response.get("data", {}).get("activitySeriesConnection", {})
        page_nodes = [
            edge.get("node") for edge in (connection.get("edges") or []) if edge.get("node")
        ]
        nodes.extend(page_nodes)

        siemplify.LOGGER.info(
            f"Activity series page fetched: {len(page_nodes)} series "
            f"(running total: {len(nodes)})."
        )

        page_info = connection.get("pageInfo") or {}
        next_page_token = page_info.get("endCursor")
        if not page_info.get("hasNextPage") or not next_page_token:
            break

    return nodes


def partition_by_fetch_type(siemplify, event_nodes, fetch_types):
    """Route each fetched series to the RSC fetch type its lastActivityType maps to.

    Matched case-insensitively: RSC echoes lastActivityType back in its own casing
    ("Classification") rather than the filter's ("CLASSIFICATION").

    Returns:
        Dict of fetch type -> list of series nodes, covering only the selected
        fetch types. Series whose lastActivityType maps to nothing selected are
        counted and dropped.
    """
    partitioned = {fetch_type: [] for fetch_type in fetch_types}
    unrouted = 0

    for event_node in event_nodes:
        activity_type = (event_node.get("lastActivityType") or "").strip().upper()
        fetch_type = ACTIVITY_TYPE_TO_FETCH_TYPE.get(activity_type)
        if fetch_type in partitioned:
            partitioned[fetch_type].append(event_node)
        else:
            unrouted += 1

    siemplify.LOGGER.info(
        "Routed by lastActivityType: "
        + ", ".join(f"{name}={len(items)}" for name, items in partitioned.items())
        + (f", unrouted={unrouted}" if unrouted else "")
    )
    return partitioned


def fetch_snappable_identity(siemplify, manager, object_id):
    """Resolve the hierarchy identity for a series' objectId.

    Adds the identifying detail the activity series does not carry -- the
    SharePoint site URL for an O365Site, the drive owner for an O365Onedrive -- so
    a finding can be tied to the tenant object it concerns.

    Called only once an alert is definitely going to be raised: for classification
    that is after the per-objectId dedup AND after the hits count has ruled out
    objects with zero violations, so no call is spent on an object that is about to
    be skipped.

    Returns:
        The hierarchyObject dict, or {} if it could not be resolved -- a failure
        degrades the event rather than dropping the alert.
    """
    if not object_id:
        return {}
    try:
        response = manager.get_snappable_identity(fid=object_id)
        hierarchy_object = (response or {}).get("data", {}).get("hierarchyObject") or {}
        if not hierarchy_object:
            siemplify.LOGGER.info(f"No hierarchyObject returned for fid {object_id}.")
        return hierarchy_object
    except Exception as err:
        siemplify.LOGGER.error(
            f"Could not resolve hierarchy identity for fid {object_id}: {err}"
        )
        return {}


def _snapshot_fid_from_activity_info(siemplify, event_node):
    """Read the classified snapshot FID off the ClassficationResultsAvailable activity.

    RSC persists ClassificationResultsEventInfo as JSON on the activity's
    activityInfo field so consumers can correlate the event to the exact
    classified snapshot without inferring it from a timestamp.

    Returns the snapshotFid string, or None if no activity carries one.
    """
    activity_nodes = (event_node.get("activityConnection") or {}).get("nodes") or []
    candidates = [
        node
        for node in activity_nodes
        if CLASSIFICATION_ACTIVITY_MESSAGE_FILTER in (node.get("message") or "")
    ] or activity_nodes

    for node in candidates:
        raw = node.get("activityInfo")
        if not raw:
            continue
        try:
            info = json.loads(raw)
        except (TypeError, ValueError) as err:
            siemplify.LOGGER.error(
                f"activityInfo is not JSON: {raw!r} ({err})"
            )
            continue
        snapshot_fid = (info or {}).get("snapshotFid")
        if snapshot_fid:
            return snapshot_fid
        siemplify.LOGGER.info(
            f"activityInfo present but carries no snapshotFid: {info}"
        )
    return None


def build_classification_alerts(
    siemplify,
    manager,
    environment_common,
    event_nodes,
    event_field_parameter,
    product_field_name,
    is_test_run,
):
    """Build alerts from already-fetched Sonar classification activity series.

    Unchanged pipeline: keep the series whose activity message reports available
    results, dedup by objectId, resolve the closest snapshot, then read policyObj
    and alert on violations > 0. Only the fetch moved out -- the CLASSIFICATION
    series now arrive from the shared activitySeriesConnection sweep in main().
    """
    alerts = []

    # ----------------------------------------------------------------
    # Step 1 + 2: Filter by classification message, then dedup by
    #             objectId keeping the latest-lastUpdated entry.
    # ----------------------------------------------------------------
    latest_per_object = {}

    for node in event_nodes:
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
        f"Classification: {len(event_nodes)} series; {len(latest_per_object)} unique "
        "objects after filter + dedup."
    )

    # ----------------------------------------------------------------
    # Steps 3-4: For each deduplicated object, resolve snapshot ->
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
            # Step 4: Retrieve snapshot FID from the event
            snapshot_id = _snapshot_fid_from_activity_info(siemplify, event_node)

            if not snapshot_id:
                siemplify.LOGGER.info(
                    f"Skipping {activity_series_id}: no snapshot for {object_id}."
                )
                continue

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

            # Only now, with the alert certain to be raised, is the identity
            # lookup worth a call -- deduped and past the violations > 0 gate.
            hierarchy_object = fetch_snappable_identity(siemplify, manager, object_id)

            # Build AlertInfo
            alert_info = build_alert_info(
                siemplify,
                RubrikClassificationAlertDatamodel(
                    event_node, policy_obj, snapshot_id, hierarchy_object
                ),
                environment_common,
                event_field_parameter,
                product_field_name,
                is_test_run,
            )
            if alert_info is None:
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

    siemplify.LOGGER.info(f"Classification events produced {len(alerts)} alert(s).")
    return alerts


def fetch_violation_status(siemplify, manager, series_id, violation_type):
    """Look up one field -- the violation's status -- for an activity series.

    The activity series carries no status enum, and the Close Duplicate Violation
    Alerts Job cannot decide whether a violation is finished without one. That is
    the whole reason for this call, so only `status` is taken from the response:
    the rest of the policyViolation record duplicates what the series already
    provides and would just add fields to the case wall.

    The violation is fetched by its activitySeriesId, which RSC also accepts as
    the violation id. IR is queried with every policy type
    (ALL_IR_POLICY_TYPES): the details query requires policyTypes and the series
    does not say which one applies.

    Returns:
        The POLICY_VIOLATION_STATUS_* string, or "" if it could not be resolved --
        a failed lookup degrades the alert (no status) rather than failing the
        whole series.
    """
    try:
        if violation_type == RSC_FETCH_TYPE_DSPM:
            data = manager.get_dspm_violation_details(series_id)
        else:
            data = manager.get_ir_violation_details(series_id, ALL_IR_POLICY_TYPES)
        return ((data or {}).get("policyViolation") or {}).get("status") or ""
    except Exception as err:
        siemplify.LOGGER.error(
            f"Could not resolve {violation_type} violation status for series "
            f"{series_id}: {err}"
        )
        return ""


def build_violation_alerts(
    siemplify,
    manager,
    environment_common,
    event_nodes,
    violation_type,
    event_field_parameter,
    product_field_name,
    is_test_run,
    is_timed_out=None,
    window=None,
):
    """Build DSPM / IR alerts from already-fetched activity series nodes.

    One builder covers both: DSPM (SECURITY_VIOLATION) and IR (IDENTITY_VIOLATION
    / IDENTITY_ALERTS) series are structurally identical, differing only in the
    lastActivityType that routed them here.

    Each series costs one extra API call to resolve its violation status (see
    fetch_violation_status), so is_timed_out is polled per series: enrichment is
    the most expensive part of a run, and a large window can hold hundreds of
    series.

    Returns:
        (alerts, timed_out) -- timed_out is True if the loop stopped early, which
        makes main() discard the run rather than ingest a partially enriched
        batch.
    """
    alerts = []

    for event_node in event_nodes:
        series_id = event_node.get("activitySeriesId") or event_node.get("id", "")

        if is_timed_out is not None and is_timed_out():
            siemplify.LOGGER.info(
                f"Timeout is approaching while enriching {violation_type} "
                f"({len(alerts)} of {len(event_nodes)} series done). Stopping."
            )
            return alerts, True

        try:
            violation_status = fetch_violation_status(
                siemplify, manager, series_id, violation_type
            )
            # DSPM findings are about a snappable, so the hierarchy identity
            # applies. IR series describe an identity and carry their own
            # resourceMetadata, so the lookup is skipped for them.
            hierarchy_object = (
                fetch_snappable_identity(siemplify, manager, event_node.get("objectId"))
                if violation_type == RSC_FETCH_TYPE_DSPM
                else {}
            )
            datamodel = RubrikActivityViolationAlertDatamodel(
                event_node, violation_type, violation_status, hierarchy_object, window
            )
            latest = datamodel.get_latest_activity_node()

            # A series can be pulled in by activity that is not itself alertable --
            # an audit-log download, or an entry that predates this window and was
            # ingested by an earlier run. Both leave nothing to raise, and building
            # an alert anyway would re-emit an old entry on every run.
            if not latest:
                siemplify.LOGGER.info(
                    f"Skipping {violation_type} series {series_id}: no activity entry "
                    "inside this run's window once audit-log entries are excluded."
                )
                continue

            siemplify.LOGGER.info(
                f"Processing {violation_type} series {series_id}: "
                f"latest activity {latest.get('id')} at {latest.get('time')} "
                f"({event_node.get('lastActivityType')}), "
                f"status {violation_status or 'unresolved'}."
            )

            alert_info = build_alert_info(
                siemplify,
                datamodel,
                environment_common,
                event_field_parameter,
                product_field_name,
                is_test_run,
            )
            if alert_info is None:
                continue

            alerts.append(alert_info)
            siemplify.LOGGER.info(f"Alert added: {alert_info.ticket_id} ({alert_info.name}).")

        except Exception as e:
            siemplify.LOGGER.error(
                f"Failed to process {violation_type} series {series_id}. Error: {e}"
            )
            siemplify.LOGGER.exception(e)
            if is_test_run:
                raise

    siemplify.LOGGER.info(
        f"{violation_type}: {len(event_nodes)} series processed; "
        f"produced {len(alerts)} alert(s)."
    )
    return alerts, False


@output_handler
def main(is_test_run):
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    siemplify.LOGGER.info(f"Connector version: {CONNECTOR_VERSION}")

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
        # ----------------------------------------------------------------
        # Validate every input before touching the API. SecOps has no
        # multi-select input type for connectors, so each filter arrives as
        # hand-typed comma-separated text and is checked against the exact
        # values its parameter description documents; an unrecognised value
        # fails the run naming the parameter and listing what is accepted.
        # ----------------------------------------------------------------
        service_account_json = validate_service_account_json(service_account_json)

        # Which sources to ingest. Required, with no default: extracted as
        # non-mandatory so an empty value produces the message below instead of a
        # raw "mandatory parameter missing" error.
        fetch_types = extract_multi_select_param(
            siemplify,
            "RSC Fetch Types",
            RSC_FETCH_TYPE_ENUM_MAP,
        )
        if not fetch_types:
            raise ValueError(
                ERROR_NO_RSC_FETCH_TYPES.format(", ".join(RSC_FETCH_TYPE_ENUM_MAP.keys()))
            )
        siemplify.LOGGER.info(f"Selected RSC fetch types: {', '.join(fetch_types)}.")

        # The severity / category / sensitivity / policy-type / identity-tag
        # filters are gone: activitySeriesConnection's ActivitySeriesFilter has no
        # equivalent inputs, so they could not be honoured against this endpoint.
        # Every series of the selected activity types is fetched instead.

        # Validate the search window (must not exceed MAX_SEARCH_TIME_PERIOD_DAYS).
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
        # Time window, shared by all three sources. from_timestamp comes from
        # the checkpoint (last run's window end) or falls back to now - search
        # period on the first run. to_timestamp is always now.
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

        environment_common = GetEnvironmentCommonFactory.create_environment_manager(
            siemplify,
            "",
            "",
        )

        # ----------------------------------------------------------------
        # All three fetch types come from activitySeriesConnection, so the
        # window is swept once for the union of the selected types' activity
        # types and the results routed afterwards -- rather than one sweep per
        # type over the same window.
        #
        # A type not selected is simply never requested. Note the checkpoint is
        # a single timestamp shared by all three (by design), so it still
        # advances at the end of a successful run even though a deselected type
        # was never fetched; that type's coverage for this window is then
        # permanently lost if it is re-selected on a later run. This is an
        # accepted trade-off of the single shared checkpoint, not a bug to be
        # fixed per-type; deselected_labels below only makes the risk visible in
        # the log when it applies.
        # ----------------------------------------------------------------
        deselected_labels = [
            fetch_type
            for fetch_type in RSC_FETCH_TYPE_ACTIVITY_TYPES
            if fetch_type not in fetch_types
        ]
        for fetch_type in deselected_labels:
            siemplify.LOGGER.info(f"{fetch_type} not selected in 'RSC Fetch Types'. Skipping.")

        activity_types = [
            activity_type
            for fetch_type in RSC_FETCH_TYPE_ACTIVITY_TYPES
            if fetch_type in fetch_types
            for activity_type in RSC_FETCH_TYPE_ACTIVITY_TYPES[fetch_type]
        ]

        timed_out = is_approaching_timeout(connector_starting_time, python_process_timeout)
        partitioned = {}

        if timed_out:
            siemplify.LOGGER.info(
                "Timeout is approaching before fetching. Skipping the activity series sweep."
            )
        else:
            siemplify.LOGGER.info("=============== Activity Series Sweep ===============")
            event_nodes = fetch_activity_series(
                siemplify, manager, activity_types, from_iso, to_iso
            )
            partitioned = partition_by_fetch_type(siemplify, event_nodes, fetch_types)

        # Build alerts per selected type. Every builder now makes per-series
        # enrichment calls -- Classification resolves snapshot + policyObj, and
        # DSPM/IR resolve the policyViolation record for its status -- so each
        # builder polls the timeout itself and reports whether it stopped early.
        def violation_timeout_check():
            return is_approaching_timeout(connector_starting_time, python_process_timeout)

        build_phases = (
            (
                RSC_FETCH_TYPE_CLASSIFICATION,
                "Classification Events",
                lambda nodes: (
                    build_classification_alerts(
                        siemplify,
                        manager,
                        environment_common,
                        nodes,
                        event_field_parameter,
                        product_field_name,
                        is_test_run,
                    ),
                    False,
                ),
            ),
            (
                RSC_FETCH_TYPE_DSPM,
                "DSPM Violations",
                lambda nodes: build_violation_alerts(
                    siemplify,
                    manager,
                    environment_common,
                    nodes,
                    RSC_FETCH_TYPE_DSPM,
                    event_field_parameter,
                    product_field_name,
                    is_test_run,
                    violation_timeout_check,
                    (from_iso, to_iso),
                ),
            ),
            (
                RSC_FETCH_TYPE_IR,
                "IR Violations",
                lambda nodes: build_violation_alerts(
                    siemplify,
                    manager,
                    environment_common,
                    nodes,
                    RSC_FETCH_TYPE_IR,
                    event_field_parameter,
                    product_field_name,
                    is_test_run,
                    violation_timeout_check,
                    (from_iso, to_iso),
                ),
            ),
        )

        for fetch_type, label, build_alerts in build_phases:
            nodes = partitioned.get(fetch_type)
            if not nodes:
                continue

            siemplify.LOGGER.info(f"=============== {label} ===============")

            if timed_out or is_approaching_timeout(
                connector_starting_time, python_process_timeout
            ):
                timed_out = True
                siemplify.LOGGER.info(f"Timeout is approaching. Skipping {label}.")
                continue

            phase_alerts, phase_timed_out = build_alerts(nodes)
            alerts.extend(phase_alerts)
            timed_out = timed_out or phase_timed_out

        # ----------------------------------------------------------------
        # All alerts gathered. Ingest only if we are not approaching the
        # process timeout; otherwise exit gracefully without ingesting or
        # advancing the checkpoint so the next run redoes this window.
        # ----------------------------------------------------------------
        # NOTE: return_package finalizes and flushes the connector output, so
        # any logging or checkpoint write MUST happen before it — otherwise
        # those log lines never reach the debug output.
        if timed_out or is_approaching_timeout(connector_starting_time, python_process_timeout):
            siemplify.LOGGER.info(
                "Timeout is approaching. Exiting gracefully without ingesting; "
                "checkpoint unchanged."
            )
            package = []
        else:
            if deselected_labels:
                siemplify.LOGGER.info(
                    "WARNING: advancing the shared checkpoint to "
                    f"'{to_iso}' despite {', '.join(deselected_labels)} being "
                    "absent from this run's 'RSC Fetch Types' selection. "
                    "Classification, DSPM and IR share a single checkpoint "
                    "timestamp by design, so if it is re-selected on a later "
                    f"run it will resume from '{to_iso}' onward -- anything "
                    f"updated in RSC between '{from_iso}' and '{to_iso}' for "
                    "that source will never be fetched."
                )
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
