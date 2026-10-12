# Rubrik Security Cloud - Close Duplicate Violation Alerts Job
#
# Problem: RSC records a violation again on every status transition, so the same
# violation lands in SecOps more than once. The connector polls
# activitySeriesConnection and raises one alert per new activityConnection entry
# -- so "detected", "changed status to in progress" and "was remediated" are
# three separate, immutable alerts for one violation. A playbook-driven status
# update (e.g. "Update Violation Status -> Remediated") comes back the same way.
# This job cleans those up: it groups open cases' Rubrik alerts per violation,
# finds the latest status-carrying alert in each group, and if that status is
# terminal (POLICY_VIOLATION_STATUS_REMEDIATED / _CLOSED / _DISMISSED), closes
# every case touched by that violation -- unless a case also holds a *different*,
# still-open violation, in which case it is left alone (see
# _decide_and_apply_case_closures).
#
# Both the violation identity and its status are read straight off the fields
# the connector ingests, so this job stays aligned with the connector's event
# payload:
#
#   identity   activitySeriesId, straight from the activity series. Every alert
#              of one violation shares it, and it is also what the connector sets
#              as the case's grouping identifier, so grouping here lands on the
#              same set of alerts the case does.
#   status     the one field the connector resolves from RSC per series. An alert
#              whose lookup failed carries no status, and such a violation is
#              grouped but never closed -- there is no evidence it finished.
#
# `status` is the single status field on the event; there is no second spelling to
# reconcile.
#
# The 24-hour grouping window makes one extra step necessary. SecOps merges alerts
# into the same case only within 24 hours of it opening, so a violation detected on
# day 0 and remediated on day 4 raises its terminal alert into a BRAND NEW case.
# The original case is left with an IN_PROGRESS alert as its newest, and the
# checkpoint guarantees it is never re-fetched -- so it would stay open forever.
# Step 2b closes that gap: for every violation that reached a terminal status, it
# searches by case name (which equals the alert name, and is identical across all
# of a violation's transitions) for the violation's other open cases, and folds
# their alerts into the same violation group. Identity is then confirmed by
# activitySeriesId, since distinct violations of the same policy on the same object
# share a name.

from __future__ import annotations

import json
from datetime import datetime, timezone

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyDataModel import (
    CaseFilterOperatorEnum,
    CaseFilterSortByEnum,
    CaseFilterSortOrderEnum,
)
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from ..core.constants import (
    RSC_FETCH_TYPE_DSPM,
    RSC_FETCH_TYPE_IR,
    TERMINAL_POLICY_VIOLATION_STATUSES,
)

SCRIPT_NAME = "Rubrik Security Cloud - Close Duplicate Violation Alerts Job"

MS_PER_DAY = 24 * 60 * 60 * 1000

# Hard ceiling on how many candidate open case IDs are fetched from SOAR in
# Step 1, independent of the "Max Cases To Process" job param -- see
# _validate_job_params for how the two interact.
FETCH_MAX_RESULTS = 10000

# Hard ceiling on "Lookback Days" -- large values don't change how many cases
# are fetched (still capped at FETCH_MAX_RESULTS), but they do make Step 1's
# SOAR query scan a much wider case history for no benefit, contributing to
# the same processing-timeout risk as an oversized "Max Cases To Process".
MAX_LOOKBACK_DAYS = 100

# Ceiling on previously-unseen related cases Step 2b fetches per run. This is the
# ONLY bound on the work that step can create: get_cases_by_filter has no
# server-side max_results, and the search is not time-bounded either. Cases beyond
# the ceiling are picked up by later runs; the run log says how many were skipped.
MAX_RELATED_CASES_TO_INSPECT = 500

# SOAR case status codes for get_cases_by_filter's `statuses` filter. Note this is
# a DIFFERENT encoding from get_cases_ids_by_filter, which takes the strings
# "OPEN"/"CLOSE"/"BOTH" -- mixing the two silently returns nothing.
CASE_STATUS_FILTER_OPEN = 1


# Case status integer returned by `_get_case_by_id` for OPEN cases (matches
# the constant already used by the DRP Deduplication Job for the same SDK).
STATUS_OPEN = 1

# Job-scoped context key the checkpoint is persisted under -- same key naming
# convention as CASES_TIMESTAMP_DB_KEY in the Vectra RUX "Expire Inactive
# Detections" job, which uses the identical get/set_scoped_job_context_property
# checkpoint pattern this job now mirrors.
CASES_TIMESTAMP_DB_KEY = "cases_timestamp"

# Event fields read off an ingested alert, looked up inside a security_event's
# `additional_properties` bag, e.g.:
#   alert["security_events"][0]["additional_properties"]["activitySeriesId"]
#   alert["security_events"][0]["additional_properties"]["status"]
# These are exactly the names the connector writes, so the job reads the
# violation's own identity and lifecycle state rather than inferring them.
#
#   activitySeriesId    the violation's identity, and the ONLY one. It comes from
#                       the activity series itself, so it is on every DSPM/IR
#                       alert regardless of whether the connector's status lookup
#                       succeeded, and it is also what the connector sets as the
#                       case grouping identifier.
#   status              the POLICY_VIOLATION_STATUS_* enum verbatim, the only
#                       field the connector takes from the violation lookup. An
#                       alert whose lookup failed has none, and Step 3 leaves such
#                       a violation open rather than inferring one.
#
# policyViolationId is deliberately NOT read. The connector takes only `status`
# from the violation lookup, so the record's id never reaches the event -- reading
# it would only ever match alerts from an older build, and mixing the two ids
# splits one violation across two groups, which is exactly the failure the
# 24h-grouping fix exists to prevent.
#
# "status" is safe to read unqualified: the connector flattens nested payload
# fields under their full path, so an identity's own status arrives as
# violation_resourceMetadata_metadata_status and cannot be confused with the
# violation's.
_SERIES_ID_KEYS = ("activitySeriesId",)
_STATUS_KEYS = ("status",)
_EVENT_NAME_KEYS = ("eventName",)
_VIOLATION_TYPE_KEYS = ("violationType",)

# The alert's own name, used by Step 2b to find the violation's other cases. The
# connector composes it from the message's severity and policy plus the series'
# objectName, so it is IDENTICAL across every transition of one violation -- which
# is what makes it usable as a case-name search key. Read off the alert rather
# than an event field because it is the case's name that is being matched.
_ALERT_NAME_KEYS = ("name", "Name")

# Only these violationType values get a violation id at all -- see
# _extract_violation_id for why classification must be excluded.
_VIOLATION_TYPES = {RSC_FETCH_TYPE_DSPM, RSC_FETCH_TYPE_IR}

# Fallback source for the violation id: the GenericEntity the TDD's Ontology
# Mapping section uses to enforce case grouping by violation id. Kept so a case
# whose alert carries the id only as a mapped entity still groups correctly.
_GENERIC_ENTITY_TYPES = {"genericentity", "generic_entity", "generic entity"}


def _validate_job_params(siemplify, max_cases, lookback_days):
    """Reject non-positive or oversized "Max Cases To Process" / "Lookback
    Days" values instead of letting them silently change job behavior or
    drive a Python processing timeout: max_cases <= 0 would truncate all_ids
    to empty at the Step 1 cap (job "succeeds" having inspected nothing),
    lookback_days <= 0 pushes lookback_ms to now-or-later (quietly dropping
    the intended time filter instead of erroring), and either value set too
    high risks the same processing timeout reported in RDIR-21 -- up to
    FETCH_MAX_RESULTS candidate cases, each fetched and inspected in a
    synchronous per-case loop in Step 2.
    """
    errors = []
    if max_cases <= 0:
        errors.append(
            "'Max Cases To Process' must be a positive integer, got {}.".format(max_cases)
        )
    elif max_cases > FETCH_MAX_RESULTS:
        errors.append(
            "'Max Cases To Process' must not exceed {}, got {}.".format(
                FETCH_MAX_RESULTS, max_cases
            )
        )
    if lookback_days <= 0:
        errors.append(
            "'Lookback Days' must be a positive integer, got {}.".format(lookback_days)
        )
    elif lookback_days > MAX_LOOKBACK_DAYS:
        errors.append(
            "'Lookback Days' must not exceed {}, got {}.".format(
                MAX_LOOKBACK_DAYS, lookback_days
            )
        )
    if errors:
        for err in errors:
            siemplify.LOGGER.error(err)
        raise ValueError(" ".join(errors))


def _fetch_checkpoint_timestamp(siemplify):
    """Read the persisted checkpoint (unix ms). 0 if never saved."""
    try:
        raw = siemplify.get_scoped_job_context_property(property_key=CASES_TIMESTAMP_DB_KEY)
    except Exception as e:
        siemplify.LOGGER.error("Failed reading checkpoint: {}".format(e))
        return 0
    if raw is None:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _get_last_success_time(siemplify, lookback_days):
    """Resolve this run's "from" timestamp: resume from the last checkpoint,
    but never further back than `lookback_days` ago -- same bound used by the
    Vectra RUX "Expire Inactive Detections" job's get_last_success_time_for_job,
    so a stale checkpoint (e.g. the job was paused) can't balloon this run's
    fetch window back to FETCH_MAX_RESULTS-cap territory.
    """
    last_checkpoint = _fetch_checkpoint_timestamp(siemplify)
    now_ms = unix_now()
    offset_ms = int(lookback_days) * MS_PER_DAY
    if now_ms - last_checkpoint > offset_ms:
        return now_ms - offset_ms
    return last_checkpoint


def _save_checkpoint_timestamp(siemplify, new_timestamp):
    """Persist `new_timestamp` (unix ms) as the checkpoint for the next run."""
    try:
        siemplify.set_scoped_job_context_property(
            property_key=CASES_TIMESTAMP_DB_KEY,
            property_value=json.dumps(new_timestamp),
        )
        siemplify.LOGGER.info("Saved checkpoint - {}.".format(new_timestamp))
    except Exception as e:
        siemplify.LOGGER.error("Failed saving checkpoint: {}".format(e))


@output_handler
def main() -> None:
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("=== Rubrik Close Duplicate Violation Alerts Job started ===")

    rule_generator_filter = siemplify.extract_job_param(
        param_name="Rule Generator",
        default_value="",
        is_mandatory=False,
        print_value=True,
    )
    environment_filter = siemplify.extract_job_param(
        param_name="Environment",
        default_value="",
        is_mandatory=False,
        print_value=True,
    )
    max_cases = siemplify.extract_job_param(
        param_name="Max Cases To Process",
        input_type=int,
        default_value=2000,
        is_mandatory=True,
        print_value=True,
    )
    lookback_days = siemplify.extract_job_param(
        param_name="Lookback Days",
        input_type=int,
        default_value=7,
        is_mandatory=True,
        print_value=True,
    )
    dry_run = siemplify.extract_job_param(
        param_name="Dry Run",
        input_type=bool,
        default_value=True,
        is_mandatory=False,
        print_value=True,
    )
    close_root_cause = siemplify.extract_job_param(
        param_name="Close Root Cause",
        default_value="Normal behavior",
        is_mandatory=False,
        print_value=True,
    )
    close_reason = siemplify.extract_job_param(
        param_name="Close Reason",
        default_value="NotMalicious",
        is_mandatory=False,
        print_value=True,
    )
    comment_prefix = siemplify.extract_job_param(
        param_name="Comment Prefix",
        default_value="[Rubrik Dedup]",
        is_mandatory=False,
        print_value=True,
    )

    rule_generator_allowlist = [
        rg.strip() for rg in rule_generator_filter.split(",") if rg.strip()
    ]
    # Passed to both case searches as the SDK's `environments` filter, which takes
    # a list. None rather than [] when unset: an empty list is a filter matching
    # nothing on some SOAR builds, whereas None is unambiguously "no filter".
    environments = [
        env.strip() for env in (environment_filter or "").split(",") if env.strip()
    ] or None

    _validate_job_params(siemplify, max_cases=max_cases, lookback_days=lookback_days)

    if environments:
        siemplify.LOGGER.info(
            "Scoping to cases in environment(s) {}. Cases in any other environment "
            "are not fetched, so their violations are neither inspected nor "
            "closed.".format(environments)
        )
    else:
        siemplify.LOGGER.info(
            "No Environment filter configured -- fetching cases across ALL environments."
        )

    if rule_generator_allowlist:
        siemplify.LOGGER.info(
            "Scoping to alerts whose rule_generator contains any of {} "
            "(case-insensitive substring match).".format(rule_generator_allowlist)
        )
    else:
        siemplify.LOGGER.info(
            "No Rule Generator filter configured -- processing alerts across ALL open "
            "cases in the lookback window. Non-Rubrik alerts are naturally excluded "
            "because they won't yield an extractable violation id."
        )

    # ── Step 1: fetch candidate open case IDs ───────────────────────────────
    # Filter on start_time OR update_time (not start_time alone): a case can
    # have been created long before the lookback window and still be exactly
    # what this job needs to catch, if it just received a fresh duplicate
    # alert (which bumps the case's update_time, not its start_time). Using
    # start_time alone -- the pattern the DRP Deduplication Job uses, which
    # doesn't apply here since that job's "primary = oldest" logic genuinely
    # needs creation time -- would silently make this job blind to any
    # still-open case older than "Lookback Days", no matter how recently a
    # new duplicate alert landed in it. sort_by=UPDATE_TIME + ASC (oldest
    # update first) means that if the open-case count exceeds max_results,
    # the cases most overdue for a check are the ones kept, not dropped --
    # same anti-starvation ordering used by bmc_remedy_itsm's sync job.
    lookback_ms = _get_last_success_time(siemplify, lookback_days)
    siemplify.LOGGER.info(
        "Using checkpoint - {} (bounded by lookback {} days) to fetch open "
        "cases.".format(lookback_ms, lookback_days)
    )
    try:
        all_ids = (
            siemplify.get_cases_ids_by_filter(
                status="OPEN",
                start_time_from_unix_time_in_ms=lookback_ms,
                update_time_from_unix_time_in_ms=lookback_ms,
                operator=CaseFilterOperatorEnum.OR,
                sort_by=CaseFilterSortByEnum.UPDATE_TIME,
                sort_order=CaseFilterSortOrderEnum.ASC,
                max_results=FETCH_MAX_RESULTS,
                environments=environments,
            )
            or []
        )
    except Exception as e:
        siemplify.LOGGER.error("Failed to fetch case IDs: {}".format(e))
        raise

    all_ids = list(dict.fromkeys(all_ids))  # dedupe, preserve order
    siemplify.LOGGER.info(
        "Fetched {} open case IDs (lookback {} days).".format(len(all_ids), lookback_days)
    )

    if len(all_ids) > max_cases:
        siemplify.LOGGER.info("Capping to {} cases (Max Cases To Process).".format(max_cases))
        all_ids = all_ids[:max_cases]

    # ── Step 2: fetch full cases, extract + group Rubrik alerts ─────────────
    # violation id -> list of {"case_id", "alert_identifier", "event_name",
    #                          "timestamp", "status", "alert_name"}
    alerts_by_violation = {}
    stats = {"skipped_no_violation_id": 0, "inspected_cases": 0, "last_case_timestamp": None}
    inspected_ids = set()

    for cid in all_ids:
        _inspect_case(
            siemplify=siemplify,
            cid=cid,
            rule_generator_allowlist=rule_generator_allowlist,
            alerts_by_violation=alerts_by_violation,
            stats=stats,
            inspected_ids=inspected_ids,
        )

    # ── Step 2b: pull in earlier cases of terminal violations ───────────────
    # Must run before the counters below are read, since it inspects more cases.
    _expand_to_related_cases(
        siemplify=siemplify,
        alerts_by_violation=alerts_by_violation,
        stats=stats,
        inspected_ids=inspected_ids,
        rule_generator_allowlist=rule_generator_allowlist,
        environments=environments,
    )

    skipped_no_violation_id = stats["skipped_no_violation_id"]
    inspected_cases = stats["inspected_cases"]
    last_case_timestamp = stats["last_case_timestamp"]

    siemplify.LOGGER.info(
        "Inspected {} open case(s) with matching Rubrik alerts. Found {} distinct "
        "violation(s). Skipped {} alert(s) with no activitySeriesId (non-Rubrik, or "
        "classification, which carries no violation).".format(
            inspected_cases,
            len(alerts_by_violation),
            skipped_no_violation_id,
        )
    )

    new_checkpoint = last_case_timestamp + 1 if last_case_timestamp else unix_now()
    _save_checkpoint_timestamp(siemplify, new_checkpoint)

    # ── Step 3: determine terminal/non-terminal status per violation ────────
    # violation id -> {"is_terminal", "status", "timestamp", "event_name"}
    #
    # Every transition of a violation is its own immutable alert, so the newest
    # status-carrying alert holds the violation's current state. Alerts with no
    # status at all are ignored for this decision rather than treated as open --
    # otherwise one unresolvable alert would pin an otherwise-remediated
    # violation open forever.
    violation_status = {}
    no_status_violations = 0
    for violation_id, records in alerts_by_violation.items():
        latest = _latest_status_record(records)
        if latest is None:
            # No alert for this violation carries a status: treat it as still open
            # so the case is never closed on missing information. In practice this
            # means the connector's violation lookup returned nothing for every
            # alert of this violation -- a rising count here is the signal that
            # the lookup has stopped resolving.
            no_status_violations += 1
            violation_status[violation_id] = {
                "is_terminal": False,
                "status": None,
                "timestamp": None,
                "event_name": None,
            }
            continue
        violation_status[violation_id] = {
            "is_terminal": latest["status"] in TERMINAL_POLICY_VIOLATION_STATUSES,
            "status": latest["status"],
            "timestamp": latest["timestamp"],
            "event_name": latest["event_name"],
        }

    terminal_count = sum(1 for v in violation_status.values() if v["is_terminal"])
    siemplify.LOGGER.info(
        "Violation statuses resolved: {} terminal, {} still open, {} with no status "
        "field on any alert (left open).".format(
            terminal_count,
            len(violation_status) - terminal_count - no_status_violations,
            no_status_violations,
        )
    )

    # ── Step 4: decide + apply per-case closure ──────────────────────────────
    closed_count, skipped_mixed_count, failed_count = _decide_and_apply_case_closures(
        siemplify=siemplify,
        alerts_by_violation=alerts_by_violation,
        violation_status=violation_status,
        close_root_cause=close_root_cause,
        close_reason=close_reason,
        comment_prefix=comment_prefix,
        dry_run=dry_run,
    )

    summary_message = (
        "Done. Cases closed: {} | Cases skipped (mixed open+terminal violations): {} "
        "| Failed: {} | Dry Run: {}".format(
            closed_count, skipped_mixed_count, failed_count, dry_run
        )
    )
    siemplify.LOGGER.info("=== {} ===".format(summary_message))

    if failed_count > 0:
        # SiemplifyJob.end_script() always sys.exit(0), so writing
        # EXECUTION_STATE_FAILED into the result JSON has no effect on a
        # standalone job's pass/fail status -- unlike a SiemplifyAction
        # result (consumed by the playbook engine straight from that JSON),
        # a job's scheduler reads the process exit code. Raising here is
        # what actually flips the run to Failed (@output_handler re-raises,
        # same as the Step 1 "Failed to fetch case IDs" path above).
        raise RuntimeError(summary_message)

    siemplify.end(
        summary_message,
        True,
        EXECUTION_STATE_COMPLETED,
    )


def _iter_event_additional_properties(alert):
    """Yield each `additional_properties` dict off this alert's security_events.

    `alert["security_events"][i]["additional_properties"]` holds the flat event
    fields the connector ingested, keyed by the connector's own field names.
    """
    for event in alert.get("security_events") or []:
        props = event.get("additional_properties")
        if props:
            yield props


def _extract_event_field(alert, field_names):
    """First non-empty value for any of `field_names` on this alert.

    Looks through each security_event's `additional_properties` bag, then the
    alert-level bag, then the alert's own top-level keys, so the same field is
    found regardless of which layer the platform surfaced it on.

    Args:
        alert: A `cyber_alerts` entry off a full case.
        field_names: Ordered field names to try; first match wins.

    Returns:
        The stripped string value, or "" when no field carries a value.
    """
    for props in _iter_event_additional_properties(alert):
        for name in field_names:
            value = props.get(name)
            if value:
                return str(value).strip()

    props = alert.get("additional_properties") or {}
    for name in field_names:
        value = props.get(name)
        if value:
            return str(value).strip()

    for name in field_names:
        value = alert.get(name)
        if value:
            return str(value).strip()

    return ""


def _inspect_case(
    siemplify,
    cid,
    rule_generator_allowlist,
    alerts_by_violation,
    stats,
    inspected_ids,
):
    """Fetch one open case and fold its Rubrik alerts into alerts_by_violation.

    Shared by Step 2 (the checkpoint window) and Step 2b (a violation's other
    cases, found by case name). Both must extract identically -- if Step 2b
    grouped or read status differently, a violation's alerts would split across
    two groups and neither would resolve correctly.

    `stats` is mutated in place: skipped_no_violation_id, inspected_cases and
    last_case_timestamp. `inspected_ids` guards against fetching a case twice,
    which would double-count its alerts within a violation group.

    Returns:
        True if the case was fetched and inspected, False if it was skipped
        (already seen, unfetchable, or no longer OPEN).
    """
    case_id = str(cid)
    if case_id in inspected_ids:
        return False
    inspected_ids.add(case_id)

    try:
        full_case = siemplify._get_case_by_id(case_id)
    except Exception as e:
        siemplify.LOGGER.info("Could not fetch case {}: {}".format(case_id, e))
        return False

    if full_case.get("status") != STATUS_OPEN:
        siemplify.LOGGER.info(
            "Fetched case {} but its status is not OPEN. SOAR filter anomaly or "
            "concurrent close? Skipping.".format(case_id)
        )
        return False

    stats["last_case_timestamp"] = max(
        stats["last_case_timestamp"] or 0,
        full_case.get("modification_time") or full_case.get("creation_time", 0),
    )

    case_creation_time = full_case.get("creation_time", 0)
    alerts = full_case.get("cyber_alerts", []) or []
    matched_this_case = False

    for alert in alerts:
        if rule_generator_allowlist and not _matches_rule_generator(
            alert, rule_generator_allowlist
        ):
            continue

        violation_id = _extract_violation_id(alert)
        if not violation_id:
            stats["skipped_no_violation_id"] += 1
            continue

        alert_identifier = alert.get("identifier")
        if not alert_identifier:
            continue

        timestamp = alert.get("creation_time") or case_creation_time

        alerts_by_violation.setdefault(violation_id, []).append({
            "case_id": case_id,
            "alert_identifier": alert_identifier,
            "event_name": _extract_event_field(alert, _EVENT_NAME_KEYS),
            "timestamp": timestamp,
            "status": _extract_event_field(alert, _STATUS_KEYS),
            "alert_name": _extract_event_field(alert, _ALERT_NAME_KEYS),
        })
        matched_this_case = True

    if matched_this_case:
        stats["inspected_cases"] += 1
    return True


def _latest_status_record(records):
    """The newest alert record for a violation that actually carries a status.

    Every transition of a violation is its own immutable alert, so the newest one
    holds the violation's current state. Records with no status are skipped rather
    than treated as open -- otherwise a single unresolvable alert would pin an
    otherwise-remediated violation open forever.

    Shared by Step 2b (to decide which violations are worth expanding) and Step 3
    (to decide closure), so the two can never disagree about which alert wins.

    Returns:
        The winning record, or None if no alert of this violation has a status.
    """
    status_records = [r for r in records if r["status"]]
    if not status_records:
        return None
    return max(status_records, key=lambda r: r["timestamp"] or 0)


def _expand_to_related_cases(
    siemplify,
    alerts_by_violation,
    stats,
    inspected_ids,
    rule_generator_allowlist,
    environments,
):
    """Pull in the earlier cases of every violation that has reached a terminal status.

    This is the fix for the 24-hour grouping window. A violation detected on day 0
    and remediated on day 4 raises its terminal alert into a NEW case, because the
    grouping identifier only merges alerts within 24 hours. The original case is
    left holding an IN_PROGRESS alert as its newest, and the checkpoint means it is
    never re-fetched -- so it stays open forever.

    Only terminal violations are expanded: a violation still in progress has
    nothing to close, so searching for its other cases would be wasted calls.

    Newly found cases are inspected through _inspect_case, i.e. their alerts join
    the SAME violation groups. That is what makes the fix work without a second
    closing path: Step 3 then sees the terminal alert from the new case and the
    stale one from the old case in one group and resolves the violation as
    terminal, and Step 4's existing "every violation in this case must be
    terminal" guard still protects a case that also holds unrelated open work.

    Mutates alerts_by_violation, stats and inspected_ids in place; the caller reads
    the outcome from those, so nothing is returned.
    """
    if MAX_RELATED_CASES_TO_INSPECT <= 0:
        siemplify.LOGGER.info(
            "MAX_RELATED_CASES_TO_INSPECT is 0. Skipping the related-case expansion; "
            "cases opened outside the 24h grouping window will not be closed."
        )
        return

    # Group by name, not by violation: many violations share an alert name (same
    # policy, same object), and one lookup per distinct name collapses the calls.
    names_to_search = set()
    for records in alerts_by_violation.values():
        latest = _latest_status_record(records)
        if not latest or latest["status"] not in TERMINAL_POLICY_VIOLATION_STATUSES:
            continue
        for record in records:
            if record["alert_name"]:
                names_to_search.add(record["alert_name"])

    if not names_to_search:
        siemplify.LOGGER.info(
            "No violation reached a terminal status this run. Nothing to expand."
        )
        return

    siemplify.LOGGER.info(
        "Searching {} distinct alert name(s) for earlier cases of terminal "
        "violations.".format(len(names_to_search))
    )

    related_found = 0
    related_inspected = 0
    budget_exhausted = False

    for alert_name in sorted(names_to_search):
        candidate_ids = _find_related_case_ids(siemplify, alert_name, environments)
        # Already-inspected ids are the common case, not an anomaly: the case that
        # produced this name in Step 2 matches its own name search.
        new_ids = [cid for cid in candidate_ids if cid not in inspected_ids]
        related_found += len(new_ids)
        # Both counts, because they fail for opposite reasons: 0 matched means the
        # filter itself found nothing (name, status, environment or response shape),
        # while matched>0 with new=0 means the filter works and the only case
        # bearing this name is one already inspected this run.
        siemplify.LOGGER.info(
            "Name {!r}: {} case(s) matched the filter, {} of them not yet "
            "inspected. Matched ids: {}".format(
                alert_name, len(candidate_ids), len(new_ids), candidate_ids
            )
        )

        for cid in new_ids:
            if related_inspected >= MAX_RELATED_CASES_TO_INSPECT:
                budget_exhausted = True
                break
            if _inspect_case(
                siemplify=siemplify,
                cid=cid,
                rule_generator_allowlist=rule_generator_allowlist,
                alerts_by_violation=alerts_by_violation,
                stats=stats,
                inspected_ids=inspected_ids,
            ):
                related_inspected += 1

        if budget_exhausted:
            break

    if budget_exhausted:
        siemplify.LOGGER.info(
            "Hit MAX_RELATED_CASES_TO_INSPECT ({}). {} further related case(s) were "
            "found but NOT inspected this run -- the next run picks them up.".format(
                MAX_RELATED_CASES_TO_INSPECT, related_found - related_inspected
            )
        )

    siemplify.LOGGER.info(
        "Related-case expansion: {} name(s) searched, {} previously-unseen case(s) "
        "found, {} inspected. Cases whose alerts belong to a different violation are "
        "grouped separately and left alone.".format(
            len(names_to_search), related_found, related_inspected
        )
    )


def _find_related_case_ids(siemplify, alert_name, environments):
    """Case ids of other OPEN cases whose case name is `alert_name`.

    SecOps groups alerts into one case only within a 24-hour window, so a
    violation that is remediated days after it was detected raises its terminal
    alert into a BRAND NEW case. The original case's newest alert still reads
    IN_PROGRESS and the checkpoint guarantees it is never re-fetched, so without
    this lookup it stays open forever.

    Matching is on the case name, which equals the alert name: the connector
    composes that from the message's severity and policy plus the series'
    objectName, so it is identical across every transition of one violation.
    `case_names` is an exact match, so the name is passed verbatim.

    This deliberately uses get_cases_by_filter, NOT get_cases_ids_by_filter -- the
    latter has no name filter at all. Note the differing contract: statuses are
    ints here rather than "OPEN"/"CLOSE" strings, and there is no max_results,
    which is why the caller caps how many results it will actually inspect.

    No time bound is passed. A violation can sit in progress for arbitrarily long,
    and any window narrow enough to be cheap is also narrow enough to miss its
    original case -- which would leave that case open forever, the exact bug this
    step exists to fix. Filtering on an exact case name plus OPEN status is already
    selective, so the search is left unbounded in time.

    A name match is only a candidate: distinct violations of the same policy on
    the same object share a name. The caller confirms identity by activitySeriesId.

    `environments` is the same filter Step 1 uses. It must be applied here too --
    otherwise the Environment param would scope which cases are inspected but not
    which ones this step drags back in, and the job would close cases in
    environments it was explicitly told to leave alone.

    Returns:
        A list of case ids, or [] if the lookup failed -- a failure must not stop
        the run, it only leaves those cases unclosed until a later run retries.
    """
    try:
        response = siemplify.get_cases_by_filter(
            case_names=[alert_name],
            statuses=[CASE_STATUS_FILTER_OPEN],
            environments=environments,
        )
    except Exception as e:
        siemplify.LOGGER.error(
            "Related-case lookup failed for alert name {!r}: {}".format(alert_name, e)
        )
        return []

    case_ids = _normalize_case_ids(response)
    if not case_ids:
        # An empty result and an unrecognised envelope are indistinguishable from
        # the count alone, and _normalize_case_ids returns [] for both. Show the
        # raw payload so a shape mismatch cannot masquerade as "no matches".
        siemplify.LOGGER.info(
            "Name search for {!r} yielded no case ids. Raw response type={}, "
            "value={}".format(
                alert_name, type(response).__name__, str(response)[:500]
            )
        )
    return case_ids


def _normalize_case_ids(response):
    """Pull case ids out of a get_cases_by_filter response.

    The SDK returns json.loads(response.text) verbatim and its docstring only
    promises "case_ids", so the shape is not guaranteed to be a bare list --
    tolerate a list of ids, a list of case objects, or a wrapper dict rather than
    throwing on an unexpected envelope.
    """
    if isinstance(response, dict):
        for key in ("caseIds", "case_ids", "cases", "identifiers"):
            if key in response:
                response = response[key]
                break
        else:
            return []

    if not isinstance(response, list):
        return []

    case_ids = []
    for entry in response:
        if isinstance(entry, dict):
            value = entry.get("identifier") or entry.get("id") or entry.get("caseId")
        else:
            value = entry
        if value is not None and str(value).strip():
            case_ids.append(str(value).strip())
    return case_ids


def _extract_violation_id(alert):
    """Extract the id of the RSC violation this alert belongs to.

    Always the activitySeriesId: it is on every DSPM/IR alert, is shared by all of
    one violation's alerts, and is what the connector sets as the case grouping
    identifier -- so grouping on it here lands on the same set of alerts the case
    does. policyViolationId is not consulted at all; see the module header.

    Only alerts the connector marked as a violation are given an id. Classification
    alerts come from the same activitySeriesConnection sweep and carry an
    activitySeriesId too, but they have no violation and no status, so treating
    their series id as a violation id would create a group that can never reach a
    terminal status -- pinning its case open forever.

    The GenericEntity mapping (per the TDD's Ontology Mapping section) is the last
    resort, for a violation alert that somehow exposes its id only as a mapped
    entity. It sits inside the violation-type gate for the same reason as above.
    """
    violation_type = _extract_event_field(alert, _VIOLATION_TYPE_KEYS).upper()
    if violation_type not in _VIOLATION_TYPES:
        return ""

    activity_series_id = _extract_event_field(alert, _SERIES_ID_KEYS)
    if activity_series_id:
        return activity_series_id

    for entity in alert.get("entities") or []:
        entity_type = (entity.get("entity_type") or entity.get("type") or "").strip().lower()
        if entity_type in _GENERIC_ENTITY_TYPES:
            identifier = (entity.get("identifier") or "").strip()
            if identifier:
                return identifier

    return ""


def _matches_rule_generator(alert, rule_generator_allowlist):
    """Whether this alert's rule_generator matches any configured value.

    Matched as a case-insensitive substring rather than for equality: the
    connector sets rule_generator to the violation's composed alert name (e.g.
    "Critical severity violation of policy 'Overexposed PII' detected on
    'Admin'"), which is unique per policy and target, so an exact-match allowlist
    could never hit. Substring matching keeps the parameter usable for scoping to
    a policy name or a severity word.

    The name is composed from the message's severity and policy plus the series'
    objectName, so it stays identical across a violation's transitions -- an
    allowlist entry matches every alert of a violation, not just the one that
    happened to be worded a particular way.
    """
    rule_generator = (alert.get("rule_generator") or "").strip().lower()
    if not rule_generator:
        return False
    return any(entry.lower() in rule_generator for entry in rule_generator_allowlist)


def _format_timestamp(timestamp_ms):
    """Render an epoch-milliseconds timestamp as a human-readable UTC string,
    for use in case comments. Falls back to the raw value if it can't be
    parsed as a number (e.g. None)."""
    try:
        return (
            datetime.fromtimestamp(int(timestamp_ms) / 1000, tz=timezone.utc)
            .strftime("%Y-%m-%d %H:%M:%S UTC")
        )
    except (TypeError, ValueError, OverflowError):
        return str(timestamp_ms)


def _decide_and_apply_case_closures(
    siemplify,
    alerts_by_violation,
    violation_status,
    close_root_cause,
    close_reason,
    comment_prefix,
    dry_run,
):
    """Close every case whose Rubrik alerts belong ONLY to violation groups
    that have all reached a terminal status. A case that also holds a
    different, still-open violation is left alone entirely -- closing the
    whole case would incorrectly close an unrelated, still-active
    violation that happens to share the case.

    Returns (closed_count, skipped_mixed_count, failed_count).
    """
    case_to_violations = {}
    for violation_id, records in alerts_by_violation.items():
        for record in records:
            case_to_violations.setdefault(record["case_id"], set()).add(violation_id)

    closed_count = 0
    skipped_mixed_count = 0
    failed_count = 0

    for case_id, violation_ids in case_to_violations.items():
        statuses = {vid: violation_status[vid] for vid in violation_ids}
        non_terminal = [vid for vid, state in statuses.items() if not state["is_terminal"]]

        if non_terminal:
            if len(violation_ids) > 1:
                siemplify.LOGGER.info(
                    "Case {}: skipping -- contains {} still-open violation(s) "
                    "alongside {} terminal one(s). Leaving case open.".format(
                        case_id, len(non_terminal), len(violation_ids) - len(non_terminal)
                    )
                )
                skipped_mixed_count += 1
            # else: the single violation in this case simply isn't terminal yet
            # -- expected, not worth a log line per case on every run.
            continue

        # Every violation touching this case is terminal -> close it.
        records_in_case = [
            r for vid in violation_ids for r in alerts_by_violation[vid] if r["case_id"] == case_id
        ]
        representative_alert_id = records_in_case[0]["alert_identifier"]

        breakdown_lines = "\n".join(
            "  - violation {}: latest status={} (event={}) at {}".format(
                vid,
                statuses[vid]["status"],
                statuses[vid]["event_name"] or "N/A",
                _format_timestamp(statuses[vid]["timestamp"]),
            )
            for vid in sorted(violation_ids)
        )
        case_comment = (
            "{prefix} Attempting to auto-close this case -- every Rubrik violation in it "
            "has reached a terminal status in RSC:\n{breakdown}\n"
            "Closing {n} matching alert(s) in this case.".format(
                prefix=comment_prefix,
                breakdown=breakdown_lines,
                n=len(records_in_case),
            )
        )
        close_comment = "{} Duplicate/stale violation alert(s) -- see case comment.".format(
            comment_prefix
        )
        failure_comment = (
            "{} Failed to auto-close this case -- see job logs for details.".format(
                comment_prefix
            )
        )

        if dry_run:
            siemplify.LOGGER.info(
                "[DRY RUN] Would add comment and close case {} ({} alert(s), "
                "violation(s) {}).".format(
                    case_id, len(records_in_case), sorted(violation_ids)
                )
            )
            closed_count += 1
            continue

        try:
            siemplify.add_comment(case_comment, case_id, representative_alert_id)
            siemplify.close_case(
                root_cause=close_root_cause,
                comment=close_comment,
                reason=close_reason,
                case_id=case_id,
                alert_identifier=representative_alert_id,
            )
            siemplify.LOGGER.info(
                "Closed case {} ({} alert(s), violation(s) {}).".format(
                    case_id, len(records_in_case), sorted(violation_ids)
                )
            )
            closed_count += 1
        except Exception as e:
            failed_count += 1
            siemplify.LOGGER.error("Failed to close case {}: {}".format(case_id, e))
            try:
                siemplify.add_comment(failure_comment, case_id, representative_alert_id)
            except Exception as comment_err:
                siemplify.LOGGER.error(
                    "Additionally failed to add failure comment to case {}: {}".format(
                        case_id, comment_err
                    )
                )

    return closed_count, skipped_mixed_count, failed_count


if __name__ == "__main__":
    main()
