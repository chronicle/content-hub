from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Callable

from EnvironmentCommon import GetEnvironmentCommonFactory
from soar_sdk.SiemplifyConnectors import SiemplifyConnectorExecution
from soar_sdk.SiemplifyUtils import output_handler, unix_now
from TIPCommon.extraction import extract_connector_param
from TIPCommon.smp_time import is_approaching_timeout
from TIPCommon.utils import is_overflowed

from ..core.api_manager import APIManager
from ..core.connector_helpers import (
    TIME_FORMAT,
    extract_multi_select_param,
    read_checkpoint,
    validate_search_time_period,
    validate_service_account_json,
    write_checkpoint,
)
from ..core.constants import (
    ACTIVITY_STATUS_SUCCESS,
    ACTIVITY_SWEEP_SORT_ORDER,
    ACTIVITY_TYPE_TO_FETCH_TYPE,
    ALL_IR_POLICY_TYPES,
    CLASSIFICATION_ACTIVITY_MESSAGE_FILTER,
    CONNECTOR_NAME,
    CONNECTOR_VERSION,
    ERROR_NO_RSC_FETCH_TYPES,
    EVENTS_PAGE_SIZE,
    RSC_FETCH_TYPE_ACTIVITY_TYPES,
    RSC_FETCH_TYPE_CLASSIFICATION,
    RSC_FETCH_TYPE_DSPM,
    RSC_FETCH_TYPE_ENUM_MAP,
    RSC_FETCH_TYPE_IR,
)
from ..core.violation_datamodels import (
    RubrikActivityViolationAlertDatamodel,
    RubrikClassificationAlertDatamodel,
    SeriesContext,
)

if TYPE_CHECKING:
    from EnvironmentCommon.EnvironmentHandle import EnvironmentHandle
    from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
    from TIPCommon.types import SingleJson

    AlertDatamodel = RubrikClassificationAlertDatamodel | RubrikActivityViolationAlertDatamodel
    BuildPhase = tuple[str, str, Callable[[list[SingleJson]], tuple[list[AlertInfo], bool]]]

connector_starting_time: int = unix_now()


@dataclass
class ConnectorContext:
    """Connector parameters plus the per-run state shared by every helper.

    Populated in stages: the parameters by extract_connector_params, then the
    validated inputs, API manager, time window and environment manager by
    prepare_run. Grouped here so helpers take one context argument instead of
    threading siemplify / manager / mapping fields / test-run flag separately.
    """

    siemplify: SiemplifyConnectorExecution
    is_test_run: bool
    # Raw connector parameters.
    service_account_json: str | None = None
    verify_ssl: bool = True
    search_time_period_days: str | int | None = None
    python_process_timeout: int | None = None
    event_field_parameter: str | None = None
    product_field_name: str | None = None
    # Per-run state.
    fetch_types: list[str] = field(default_factory=list)
    deselected_labels: list[str] = field(default_factory=list)
    manager: APIManager | None = None
    environment_common: EnvironmentHandle | None = None
    from_iso: str = ""
    to_iso: str = ""


def is_timeout_approaching(context: ConnectorContext) -> bool:
    """True once the run is close enough to PythonProcessTimeout to stop working."""
    return is_approaching_timeout(connector_starting_time, context.python_process_timeout)


def build_alert_info(
    context: ConnectorContext, datamodel: AlertDatamodel
) -> AlertInfo | None:
    """Build an AlertInfo from a datamodel, returning None if it overflows."""
    siemplify = context.siemplify
    alert_info = datamodel.get_alert_info(
        context.environment_common,
        context.event_field_parameter,
        context.product_field_name,
    )

    if is_overflowed(siemplify, alert_info, context.is_test_run):
        siemplify.LOGGER.info(
            f"{alert_info.rule_generator}-{alert_info.ticket_id}"
            f"-{alert_info.environment}-{alert_info.device_product}"
            " found as overflow alert. Skipping."
        )
        return None

    return alert_info


def fetch_activity_series(
    context: ConnectorContext, activity_types: list[str]
) -> list[SingleJson]:
    """Walk every page of activitySeriesConnection for the selected activity types.

    All three fetch types come from this one endpoint, so they are fetched in a
    single paginated sweep and routed afterwards rather than queried separately --
    one pass over the window instead of one per fetch type. The window is
    context.from_iso (lastUpdatedTimeGt) to context.to_iso (lastUpdatedTimeLt);
    activity_types is already unioned across the selected fetch types.

    Returns:
        List of activitySeriesConnection nodes across every page.
    """
    siemplify = context.siemplify
    siemplify.LOGGER.info(
        f"Fetching activity series {activity_types} from {context.from_iso} to {context.to_iso}."
    )

    nodes: list[SingleJson] = []
    next_page_token: str | None = None

    while True:
        response = _fetch_activity_page(context, activity_types, next_page_token)

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


def _fetch_activity_page(
    context: ConnectorContext,
    activity_types: list[str],
    next_page_token: str | None,
) -> SingleJson:
    """Request one page of activitySeriesConnection for this run's window."""
    return context.manager.list_events(
        activity_types=activity_types,
        activity_statuses=[ACTIVITY_STATUS_SUCCESS],
        start_date=context.from_iso,
        end_date=context.to_iso,
        sort_order=ACTIVITY_SWEEP_SORT_ORDER,
        limit=EVENTS_PAGE_SIZE,
        next_page_token=next_page_token,
    )


def partition_by_fetch_type(
    siemplify: SiemplifyConnectorExecution,
    event_nodes: list[SingleJson],
    fetch_types: list[str],
) -> dict[str, list[SingleJson]]:
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


def fetch_snappable_identity(context: ConnectorContext, object_id: str | None) -> SingleJson:
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
    siemplify = context.siemplify
    if not object_id:
        return {}
    try:
        response = context.manager.get_snappable_identity(fid=object_id)
        hierarchy_object = (response or {}).get("data", {}).get("hierarchyObject") or {}
        if not hierarchy_object:
            siemplify.LOGGER.info(f"No hierarchyObject returned for fid {object_id}.")
        return hierarchy_object
    except Exception as err:
        siemplify.LOGGER.error(
            f"Could not resolve hierarchy identity for fid {object_id}: {err}"
        )
        return {}


def _snapshot_fid_from_activity_info(
    siemplify: SiemplifyConnectorExecution, event_node: SingleJson
) -> str | None:
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
            info: SingleJson = json.loads(raw)
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


def _latest_classification_per_object(
    siemplify: SiemplifyConnectorExecution,
    event_nodes: list[SingleJson],
) -> dict[str, SingleJson]:
    """Filter by classification message, then dedup by objectId.

    Keeps, per objectId, the latest-lastUpdated series that reports available
    results.
    """
    # ----------------------------------------------------------------
    # Step 1 + 2: Filter by classification message, then dedup by
    #             objectId keeping the latest-lastUpdated entry.
    # ----------------------------------------------------------------
    latest_per_object: dict[str, SingleJson] = {}

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
    return latest_per_object


def build_classification_alerts(
    context: ConnectorContext, event_nodes: list[SingleJson]
) -> list[AlertInfo]:
    """Build alerts from already-fetched Sonar classification activity series.

    Unchanged pipeline: keep the series whose activity message reports available
    results, dedup by objectId, resolve the closest snapshot, then read policyObj
    and alert on violations > 0. Only the fetch moved out -- the CLASSIFICATION
    series now arrive from the shared activitySeriesConnection sweep in main().
    """
    siemplify = context.siemplify
    alerts: list[AlertInfo] = []

    latest_per_object = _latest_classification_per_object(siemplify, event_nodes)

    # ----------------------------------------------------------------
    # Steps 3-4: For each deduplicated object, resolve snapshot ->
    #            fetch policyObj -> check violations -> build alert.
    # ----------------------------------------------------------------
    for event_node in latest_per_object.values():
        activity_series_id = event_node.get("activitySeriesId") or event_node.get("id", "")
        object_id = event_node.get("objectId", "")

        siemplify.LOGGER.info(
            f"Processing event: {activity_series_id} "
            f"(object: {event_node.get('objectName') or object_id})"
        )

        try:
            _process_classification_event(context, event_node, alerts)
        except Exception as e:
            siemplify.LOGGER.exception(
                f"Failed to process event {activity_series_id}. Error: {e}"
            )
            if context.is_test_run:
                raise

    siemplify.LOGGER.info(f"Classification events produced {len(alerts)} alert(s).")
    return alerts


def _process_classification_event(
    context: ConnectorContext, event_node: SingleJson, alerts: list[AlertInfo]
) -> None:
    """Resolve snapshot and policyObj for one series; append its alert, if any, to `alerts`."""
    siemplify = context.siemplify
    activity_series_id = event_node.get("activitySeriesId") or event_node.get("id", "")
    object_id = event_node.get("objectId", "")

    # Step 4: Retrieve snapshot FID from the event
    snapshot_id = _snapshot_fid_from_activity_info(siemplify, event_node)

    if not snapshot_id:
        siemplify.LOGGER.info(
            f"Skipping {activity_series_id}: no snapshot for {object_id}."
        )
        return

    # Step 5: Fetch policyObj and check violations
    policy_obj = _fetch_policy_obj(context, object_id, snapshot_id)

    if not policy_obj:
        siemplify.LOGGER.info(f"Skipping {activity_series_id}: no policyObj data.")
        return

    violations = policy_obj.get("rootFileResult", {}).get("hits", {}).get("violations", 0)
    if not _has_violations(siemplify, event_node, violations):
        return

    # Only now, with the alert certain to be raised, is the identity
    # lookup worth a call -- deduped and past the violations > 0 gate.
    hierarchy_object = fetch_snappable_identity(context, object_id)

    # Build AlertInfo
    alert_info = build_alert_info(
        context,
        RubrikClassificationAlertDatamodel(
            event_node,
            policy_obj,
            SeriesContext(snapshot_id=snapshot_id, hierarchy_object=hierarchy_object),
        ),
    )
    if alert_info is None:
        return

    alerts.append(alert_info)
    siemplify.LOGGER.info(
        f"Alert added: {alert_info.ticket_id} "
        f"({violations} violations, riskLevel={policy_obj.get('riskLevel')})"
    )


def _fetch_policy_obj(context: ConnectorContext, object_id: str, snapshot_id: str) -> SingleJson:
    """Fetch the classification policyObj for an object's snapshot; {} on failure."""
    policy_obj: SingleJson = {}
    try:
        pol_response = context.manager.get_classification_object_detail(
            snappable_fid=object_id,
            snapshot_fid=snapshot_id,
        )
        policy_obj = pol_response.get("data", {}).get("policyObj") or {}
    except Exception as pol_err:
        context.siemplify.LOGGER.error(
            f"Could not retrieve policyObj for {object_id}/{snapshot_id}: {pol_err}"
        )
    return policy_obj


def _has_violations(
    siemplify: SiemplifyConnectorExecution, event_node: SingleJson, violations: int
) -> bool:
    """Log the violation count for a series' object; True if it is greater than 0."""
    activity_series_id = event_node.get("activitySeriesId") or event_node.get("id", "")
    object_id = event_node.get("objectId", "")

    siemplify.LOGGER.info(
        f"Checking violation count for object {object_id}: violations={violations}."
    )
    if violations > 0:
        siemplify.LOGGER.info(
            f"Object {object_id} has violations > 0; proceeding to build alert."
        )
        return True

    siemplify.LOGGER.info(
        f"Object {object_id} has no violations (count not greater than 0). "
        f"Skipping {activity_series_id}."
    )
    return False


def fetch_violation_status(
    context: ConnectorContext, series_id: str, violation_type: str
) -> str:
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
    manager = context.manager
    try:
        if violation_type == RSC_FETCH_TYPE_DSPM:
            data = manager.get_dspm_violation_details(series_id)
        else:
            data = manager.get_ir_violation_details(series_id, ALL_IR_POLICY_TYPES)
        return ((data or {}).get("policyViolation") or {}).get("status") or ""
    except Exception as err:
        context.siemplify.LOGGER.error(
            f"Could not resolve {violation_type} violation status for series "
            f"{series_id}: {err}"
        )
        return ""


def build_violation_alerts(
    context: ConnectorContext,
    event_nodes: list[SingleJson],
    violation_type: str,
) -> tuple[list[AlertInfo], bool]:
    """Build DSPM / IR alerts from already-fetched activity series nodes.

    One builder covers both: DSPM (SECURITY_VIOLATION) and IR (IDENTITY_VIOLATION
    / IDENTITY_ALERTS) series are structurally identical, differing only in the
    lastActivityType that routed them here.

    Each series costs one extra API call to resolve its violation status (see
    fetch_violation_status), so the timeout is polled per series: enrichment is the
    most expensive part of a run, and a large window can hold hundreds of series.

    Returns:
        (alerts, timed_out) -- timed_out is True if the loop stopped early, which makes
        main() discard the run rather than ingest a partially enriched batch.
    """
    siemplify = context.siemplify
    alerts: list[AlertInfo] = []

    for event_node in event_nodes:
        series_id = event_node.get("activitySeriesId") or event_node.get("id", "")

        if is_timeout_approaching(context):
            siemplify.LOGGER.info(
                f"Timeout is approaching while enriching {violation_type} "
                f"({len(alerts)} of {len(event_nodes)} series done). Stopping."
            )
            return alerts, True

        try:
            alert_info = _build_violation_alert(context, event_node, violation_type)
            if alert_info is None:
                continue

            alerts.append(alert_info)
            siemplify.LOGGER.info(f"Alert added: {alert_info.ticket_id} ({alert_info.name}).")
        except Exception as e:
            siemplify.LOGGER.exception(
                f"Failed to process {violation_type} series {series_id}. Error: {e}"
            )
            if context.is_test_run:
                raise

    siemplify.LOGGER.info(
        f"{violation_type}: {len(event_nodes)} series processed; "
        f"produced {len(alerts)} alert(s)."
    )
    return alerts, False


def _build_violation_alert(
    context: ConnectorContext, event_node: SingleJson, violation_type: str
) -> AlertInfo | None:
    """Enrich one DSPM / IR series and build its alert; None if nothing to raise."""
    siemplify = context.siemplify
    series_id = event_node.get("activitySeriesId") or event_node.get("id", "")

    violation_status = fetch_violation_status(context, series_id, violation_type)
    # DSPM findings are about a snappable, so the hierarchy identity
    # applies. IR series describe an identity and carry their own
    # resourceMetadata, so the lookup is skipped for them.
    hierarchy_object = (
        fetch_snappable_identity(context, event_node.get("objectId"))
        if violation_type == RSC_FETCH_TYPE_DSPM
        else {}
    )
    datamodel = RubrikActivityViolationAlertDatamodel(
        event_node,
        violation_type,
        SeriesContext(
            hierarchy_object=hierarchy_object,
            violation_status=violation_status,
            window=(context.from_iso, context.to_iso),
        ),
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
        return None

    siemplify.LOGGER.info(
        f"Processing {violation_type} series {series_id}: "
        f"latest activity {latest.get('id')} at {latest.get('time')} "
        f"({event_node.get('lastActivityType')}), "
        f"status {violation_status or 'unresolved'}."
    )

    return build_alert_info(context, datamodel)


def init_siemplify(is_test_run: bool) -> SiemplifyConnectorExecution:
    """Create the connector execution and log the run header."""
    siemplify = SiemplifyConnectorExecution()
    siemplify.script_name = CONNECTOR_NAME
    siemplify.LOGGER.info(f"Connector version: {CONNECTOR_VERSION}")

    if is_test_run:
        siemplify.LOGGER.info(
            '***** This is an "IDE Play Button Run Connector once" test run ******'
        )

    siemplify.LOGGER.info("==================== Main - Param Init ====================")
    return siemplify


def extract_connector_params(
    siemplify: SiemplifyConnectorExecution, is_test_run: bool
) -> ConnectorContext:
    """Extract every connector parameter into a new ConnectorContext."""
    context = ConnectorContext(siemplify=siemplify, is_test_run=is_test_run)
    _extract_connection_params(context)
    _extract_mapping_params(context)
    return context


def _extract_connection_params(context: ConnectorContext) -> None:
    """Extract the credential, SSL, search-period and timeout parameters."""
    siemplify = context.siemplify
    context.service_account_json = extract_connector_param(
        siemplify,
        param_name="Service Account JSON",
        input_type=str,
        is_mandatory=True,
        print_value=False,
    )

    context.verify_ssl = extract_connector_param(
        siemplify,
        param_name="Verify SSL",
        input_type=bool,
        is_mandatory=False,
        default_value=True,
        print_value=True,
    )

    context.search_time_period_days = extract_connector_param(
        siemplify,
        param_name="Search Time Period In Days",
        default_value="1",
        input_type=str,
        is_mandatory=False,
        print_value=True,
    )

    context.python_process_timeout = extract_connector_param(
        siemplify,
        param_name="PythonProcessTimeout",
        input_type=int,
        is_mandatory=True,
        print_value=False,
    )


def _extract_mapping_params(context: ConnectorContext) -> None:
    """Extract the built-in event / product field-name mapping parameters."""
    # Backed by the built-in "Event Field Name" UI field (param name: EventClassId).
    context.event_field_parameter = extract_connector_param(
        context.siemplify,
        param_name="EventClassId",
        input_type=str,
        is_mandatory=False,
        default_value="eventName",
        print_value=True,
    )

    # Backed by the built-in "Product Field Name" UI field (param name: DeviceProductField).
    context.product_field_name = extract_connector_param(
        context.siemplify,
        param_name="DeviceProductField",
        input_type=str,
        is_mandatory=False,
        default_value="Rubrik Security Cloud",
        print_value=True,
    )


def validate_inputs(context: ConnectorContext) -> None:
    """Validate the credential, fetch-type and search-period inputs in place."""
    siemplify = context.siemplify
    # ----------------------------------------------------------------
    # Validate every input before touching the API. SecOps has no
    # multi-select input type for connectors, so each filter arrives as
    # hand-typed comma-separated text and is checked against the exact
    # values its parameter description documents; an unrecognised value
    # fails the run naming the parameter and listing what is accepted.
    # ----------------------------------------------------------------
    context.service_account_json = validate_service_account_json(context.service_account_json)

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
    context.fetch_types = fetch_types

    # The severity / category / sensitivity / policy-type / identity-tag
    # filters are gone: activitySeriesConnection's ActivitySeriesFilter has no
    # equivalent inputs, so they could not be honoured against this endpoint.
    # Every series of the selected activity types is fetched instead.

    # Validate the search window (must not exceed MAX_SEARCH_TIME_PERIOD_DAYS).
    context.search_time_period_days = validate_search_time_period(
        context.search_time_period_days
    )


def prepare_run(context: ConnectorContext) -> None:
    """Validate inputs, then set up the API manager, time window and environment."""
    validate_inputs(context)

    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.strftime(TIME_FORMAT)
    default_start_iso = (
        now_dt - timedelta(days=context.search_time_period_days)
    ).strftime(TIME_FORMAT)

    context.manager = APIManager(
        service_account_json=context.service_account_json,
        verify_ssl=context.verify_ssl,
        siemplify=context.siemplify,
    )

    resolve_window(context, now_iso, default_start_iso)

    context.environment_common = GetEnvironmentCommonFactory.create_environment_manager(
        context.siemplify,
        "",
        "",
    )


def resolve_window(context: ConnectorContext, now_iso: str, default_start_iso: str) -> None:
    """Set context.from_iso / context.to_iso from the checkpoint or the default."""
    siemplify = context.siemplify
    # ----------------------------------------------------------------
    # Time window, shared by all three sources. from_timestamp comes from
    # the checkpoint (last run's window end) or falls back to now - search
    # period on the first run. to_timestamp is always now.
    # ----------------------------------------------------------------
    checkpoint = {} if context.is_test_run else read_checkpoint(siemplify)
    checkpoint_from = checkpoint.get("from_timestamp")
    if checkpoint_from:
        siemplify.LOGGER.info(f"Fetched from_timestamp '{checkpoint_from}' from checkpoint.")
    else:
        siemplify.LOGGER.info(
            "No from_timestamp found in checkpoint; "
            f"defaulting to '{default_start_iso}' "
            f"(now - {context.search_time_period_days} day)."
        )
    context.from_iso = checkpoint_from or default_start_iso
    context.to_iso = now_iso


def select_activity_types(context: ConnectorContext) -> list[str]:
    """Record the deselected fetch types and return the activity types to sweep."""
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
    context.deselected_labels = [
        fetch_type
        for fetch_type in RSC_FETCH_TYPE_ACTIVITY_TYPES
        if fetch_type not in context.fetch_types
    ]
    for fetch_type in context.deselected_labels:
        context.siemplify.LOGGER.info(f"{fetch_type} not selected in 'RSC Fetch Types'. Skipping.")

    return [
        activity_type
        for fetch_type in RSC_FETCH_TYPE_ACTIVITY_TYPES
        if fetch_type in context.fetch_types
        for activity_type in RSC_FETCH_TYPE_ACTIVITY_TYPES[fetch_type]
    ]


def sweep_activity_series(
    context: ConnectorContext,
    activity_types: list[str],
) -> dict[str, list[SingleJson]]:
    """Fetch the window's series and route them by fetch type.

    Returns:
        Dict of fetch type -> list of series nodes (see partition_by_fetch_type).
    """
    siemplify = context.siemplify
    siemplify.LOGGER.info("=============== Activity Series Sweep ===============")
    event_nodes = fetch_activity_series(context, activity_types)
    return partition_by_fetch_type(siemplify, event_nodes, context.fetch_types)


def build_phases(context: ConnectorContext) -> tuple[BuildPhase, ...]:
    """(fetch type, log label, alert builder) for each type, in build order.

    Every builder makes per-series enrichment calls -- Classification resolves
    snapshot + policyObj, and DSPM/IR resolve the policyViolation record for its
    status -- so each builder reports whether it stopped early on the timeout.
    """
    return (
        (
            RSC_FETCH_TYPE_CLASSIFICATION,
            "Classification Events",
            lambda nodes: (build_classification_alerts(context, nodes), False),
        ),
        (
            RSC_FETCH_TYPE_DSPM,
            "DSPM Violations",
            lambda nodes: build_violation_alerts(context, nodes, RSC_FETCH_TYPE_DSPM),
        ),
        (
            RSC_FETCH_TYPE_IR,
            "IR Violations",
            lambda nodes: build_violation_alerts(context, nodes, RSC_FETCH_TYPE_IR),
        ),
    )


def build_alerts(
    context: ConnectorContext,
    partitioned: dict[str, list[SingleJson]],
) -> tuple[list[AlertInfo], bool]:
    """Build alerts per selected type, skipping the rest once the timeout nears.

    Returns:
        (alerts, timed_out) -- timed_out is True if any phase was skipped or
        stopped early.
    """
    siemplify = context.siemplify
    alerts: list[AlertInfo] = []
    timed_out = False

    for fetch_type, label, build_phase_alerts in build_phases(context):
        nodes = partitioned.get(fetch_type)
        if not nodes:
            continue

        siemplify.LOGGER.info(f"=============== {label} ===============")

        if timed_out or is_timeout_approaching(context):
            timed_out = True
            siemplify.LOGGER.info(f"Timeout is approaching. Skipping {label}.")
            continue

        phase_alerts, phase_timed_out = build_phase_alerts(nodes)
        alerts.extend(phase_alerts)
        timed_out = timed_out or phase_timed_out

    return alerts, timed_out


def exit_on_timeout(context: ConnectorContext) -> list[AlertInfo]:
    """Discard the run without ingesting or advancing the checkpoint.

    The next run then redoes this window instead of ingesting a partial batch.
    """
    context.siemplify.LOGGER.info(
        "Timeout is approaching. Exiting gracefully without ingesting; "
        "checkpoint unchanged."
    )
    return []


def finalize_package(context: ConnectorContext, alerts: list[AlertInfo]) -> list[AlertInfo]:
    """Return the alerts to ingest and advance the checkpoint (non-test runs)."""
    siemplify = context.siemplify
    from_iso, to_iso = context.from_iso, context.to_iso

    if context.deselected_labels:
        siemplify.LOGGER.warn(
            "Advancing the shared checkpoint to "
            f"'{to_iso}' despite {', '.join(context.deselected_labels)} being "
            "absent from this run's 'RSC Fetch Types' selection. "
            "Classification, DSPM and IR share a single checkpoint "
            "timestamp by design, so if it is re-selected on a later "
            f"run it will resume from '{to_iso}' onward -- anything "
            f"updated in RSC between '{from_iso}' and '{to_iso}' for "
            "that source will never be fetched."
        )
    siemplify.LOGGER.info(f"Ingesting {len(alerts)} alerts.")
    if not context.is_test_run:
        write_checkpoint(siemplify, to_iso)
    return alerts


def run_connector(context: ConnectorContext) -> list[AlertInfo]:
    """Run one connector cycle and return the package to hand to return_package."""
    prepare_run(context)
    activity_types = select_activity_types(context)

    if is_timeout_approaching(context):
        context.siemplify.LOGGER.info(
            "Timeout is approaching before fetching. Skipping the activity series sweep."
        )
        return exit_on_timeout(context)

    partitioned = sweep_activity_series(context, activity_types)
    alerts, timed_out = build_alerts(context, partitioned)

    # ----------------------------------------------------------------
    # All alerts gathered. Ingest only if we are not approaching the
    # process timeout; otherwise exit gracefully without ingesting or
    # advancing the checkpoint so the next run redoes this window.
    # ----------------------------------------------------------------
    if timed_out or is_timeout_approaching(context):
        return exit_on_timeout(context)

    return finalize_package(context, alerts)


@output_handler
def main(is_test_run: bool) -> None:
    siemplify = init_siemplify(is_test_run)
    context = extract_connector_params(siemplify, is_test_run)

    siemplify.LOGGER.info("------------------- Main - Started -------------------")

    try:
        package = run_connector(context)

        # NOTE: return_package finalizes and flushes the connector output, so
        # any logging or checkpoint write MUST happen before it — otherwise
        # those log lines never reach the debug output.
        siemplify.LOGGER.info("------------------- Main - Finished -------------------")
        siemplify.return_package(package)

    except Exception as e:
        siemplify.LOGGER.exception(f"Got exception on main handler. Error: {e}")
        if is_test_run:
            raise
        # On a scheduled run, always hand the framework a valid (empty) package
        # so a failure exits gracefully instead of returning null output
        # (which surfaces as a JSON deserialization ArgumentNullException).
        siemplify.return_package([])


if __name__ == "__main__":
    is_test_run = not (len(sys.argv) < 2 or sys.argv[1] == "True")
    main(is_test_run)
