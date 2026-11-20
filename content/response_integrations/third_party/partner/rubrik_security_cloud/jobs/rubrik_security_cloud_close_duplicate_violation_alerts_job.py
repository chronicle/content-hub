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
# decide_and_apply_case_closures in core/duplicate_violation_helpers.py).
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
from dataclasses import dataclass

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyDataModel import (
    CaseFilterOperatorEnum,
    CaseFilterSortByEnum,
    CaseFilterSortOrderEnum,
)
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler, unix_now

from ..core.constants import (
    CASES_TIMESTAMP_DB_KEY,
    CLOSE_DUPLICATE_VIOLATION_ALERTS_JOB_SCRIPT_NAME,
    FETCH_MAX_RESULTS,
    MAX_LOOKBACK_DAYS,
    MS_PER_DAY,
)
from ..core.duplicate_violation_helpers import (
    ClosureCounts,
    ClosureOptions,
    DedupRunState,
    decide_and_apply_case_closures,
    expand_to_related_cases,
    inspect_case,
    resolve_violation_statuses,
)


@dataclass(slots=True)
class JobParams:
    """The job's parameters, parsed into the shapes the steps consume."""

    rule_generator_allowlist: list[str]
    environments: list[str] | None
    max_cases: int
    lookback_days: int
    closure: ClosureOptions


def _validate_job_params(siemplify: SiemplifyJob, max_cases: int, lookback_days: int) -> None:
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
    errors: list[str] = []
    if max_cases <= 0:
        errors.append(
            f"'Max Cases To Process' must be a positive integer, got {max_cases}."
        )
    elif max_cases > FETCH_MAX_RESULTS:
        errors.append(
            f"'Max Cases To Process' must not exceed {FETCH_MAX_RESULTS}, got {max_cases}."
        )
    if lookback_days <= 0:
        errors.append(
            f"'Lookback Days' must be a positive integer, got {lookback_days}."
        )
    elif lookback_days > MAX_LOOKBACK_DAYS:
        errors.append(
            f"'Lookback Days' must not exceed {MAX_LOOKBACK_DAYS}, got {lookback_days}."
        )
    if errors:
        for err in errors:
            siemplify.LOGGER.error(err)
        raise ValueError(" ".join(errors))


def _fetch_checkpoint_timestamp(siemplify: SiemplifyJob) -> int:
    """Read the persisted checkpoint (unix ms). 0 if never saved."""
    try:
        raw = siemplify.get_scoped_job_context_property(property_key=CASES_TIMESTAMP_DB_KEY)
    except Exception as e:
        siemplify.LOGGER.error(f"Failed reading checkpoint: {e}")
        return 0
    if raw is None:
        return 0
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _get_last_success_time(siemplify: SiemplifyJob, lookback_days: int) -> int:
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


def _save_checkpoint_timestamp(siemplify: SiemplifyJob, new_timestamp: int) -> None:
    """Persist `new_timestamp` (unix ms) as the checkpoint for the next run."""
    try:
        siemplify.set_scoped_job_context_property(
            property_key=CASES_TIMESTAMP_DB_KEY,
            property_value=json.dumps(new_timestamp),
        )
        siemplify.LOGGER.info(f"Saved checkpoint - {new_timestamp}.")
    except Exception as e:
        siemplify.LOGGER.error(f"Failed saving checkpoint: {e}")


def _extract_scope_params(siemplify: SiemplifyJob) -> tuple[str, str, int, int]:
    """Read the params that scope which cases are fetched, in their original order.

    Returns:
        (rule_generator_filter, environment_filter, max_cases, lookback_days)
    """
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
    return rule_generator_filter, environment_filter, max_cases, lookback_days


def _extract_closure_params(siemplify: SiemplifyJob) -> ClosureOptions:
    """Read the params that shape how a case is closed, in their original order."""
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
    return ClosureOptions(
        close_root_cause=close_root_cause,
        close_reason=close_reason,
        comment_prefix=comment_prefix,
        dry_run=dry_run,
    )


def _extract_job_params(siemplify: SiemplifyJob) -> JobParams:
    """Read every job param and parse the comma-separated filters into lists."""
    rule_generator_filter, environment_filter, max_cases, lookback_days = (
        _extract_scope_params(siemplify)
    )
    closure = _extract_closure_params(siemplify)

    rule_generator_allowlist = [
        rg.strip() for rg in rule_generator_filter.split(",") if rg.strip()
    ]
    # Passed to both case searches as the SDK's `environments` filter, which takes
    # a list. None rather than [] when unset: an empty list is a filter matching
    # nothing on some SOAR builds, whereas None is unambiguously "no filter".
    environments = [
        env.strip() for env in (environment_filter or "").split(",") if env.strip()
    ] or None

    return JobParams(
        rule_generator_allowlist=rule_generator_allowlist,
        environments=environments,
        max_cases=max_cases,
        lookback_days=lookback_days,
        closure=closure,
    )


def _log_scope(siemplify: SiemplifyJob, params: JobParams) -> None:
    """Log which environments and rule generators this run is scoped to."""
    environments = params.environments
    rule_generator_allowlist = params.rule_generator_allowlist
    if environments:
        siemplify.LOGGER.info(
            f"Scoping to cases in environment(s) {environments}. Cases in any other "
            "environment are not fetched, so their violations are neither inspected "
            "nor closed."
        )
    else:
        siemplify.LOGGER.info(
            "No Environment filter configured -- fetching cases across ALL environments."
        )

    if rule_generator_allowlist:
        siemplify.LOGGER.info(
            "Scoping to alerts whose rule_generator contains any of "
            f"{rule_generator_allowlist} (case-insensitive substring match)."
        )
    else:
        siemplify.LOGGER.info(
            "No Rule Generator filter configured -- processing alerts across ALL open "
            "cases in the lookback window. Non-Rubrik alerts are naturally excluded "
            "because they won't yield an extractable violation id."
        )


def _fetch_candidate_case_ids(siemplify: SiemplifyJob, params: JobParams) -> list[str]:
    """Step 1: fetch candidate open case IDs, deduped and capped to max_cases."""
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
    lookback_days = params.lookback_days
    lookback_ms = _get_last_success_time(siemplify, lookback_days)
    siemplify.LOGGER.info(
        f"Using checkpoint - {lookback_ms} (bounded by lookback {lookback_days} days) "
        "to fetch open cases."
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
                environments=params.environments,
            )
            or []
        )
    except Exception as e:
        siemplify.LOGGER.error(f"Failed to fetch case IDs: {e}")
        raise

    all_ids = list(dict.fromkeys(all_ids))  # dedupe, preserve order
    siemplify.LOGGER.info(
        f"Fetched {len(all_ids)} open case IDs (lookback {lookback_days} days)."
    )
    return _cap_case_ids(siemplify, all_ids, params.max_cases)


def _cap_case_ids(siemplify: SiemplifyJob, all_ids: list[str], max_cases: int) -> list[str]:
    """Truncate the candidate list to "Max Cases To Process"."""
    if len(all_ids) > max_cases:
        siemplify.LOGGER.info(f"Capping to {max_cases} cases (Max Cases To Process).")
        all_ids = all_ids[:max_cases]
    return all_ids


def _log_inspection_summary(state: DedupRunState) -> None:
    """Log what Steps 2 and 2b found across all inspected cases."""
    state.siemplify.LOGGER.info(
        f"Inspected {state.inspected_cases} open case(s) with matching Rubrik alerts. "
        f"Found {len(state.alerts_by_violation)} distinct violation(s). "
        f"Skipped {state.skipped_no_violation_id} alert(s) with no activitySeriesId "
        "(non-Rubrik, or classification, which carries no violation)."
    )


def _finish_run(siemplify: SiemplifyJob, counts: ClosureCounts, dry_run: bool) -> None:
    """Log the run summary and end the job, failing it if any closure failed."""
    summary_message = (
        f"Done. Cases closed: {counts.closed} | Cases skipped (mixed open+terminal "
        f"violations): {counts.skipped_mixed} | Failed: {counts.failed} | Dry Run: {dry_run}"
    )
    siemplify.LOGGER.info(f"=== {summary_message} ===")

    if counts.failed > 0:
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


@output_handler
def main() -> None:
    siemplify = SiemplifyJob()
    siemplify.script_name = CLOSE_DUPLICATE_VIOLATION_ALERTS_JOB_SCRIPT_NAME
    siemplify.LOGGER.info("=== Rubrik Close Duplicate Violation Alerts Job started ===")

    params = _extract_job_params(siemplify)
    _validate_job_params(siemplify, max_cases=params.max_cases, lookback_days=params.lookback_days)
    _log_scope(siemplify, params)

    # ── Step 1: fetch candidate open case IDs ───────────────────────────────
    all_ids = _fetch_candidate_case_ids(siemplify, params)

    # ── Step 2: fetch full cases, extract + group Rubrik alerts ─────────────
    # Grouped into state.alerts_by_violation: violation id -> list of
    # {"case_id", "alert_identifier", "event_name", "timestamp", "status", "alert_name"}
    state = DedupRunState(
        siemplify=siemplify,
        rule_generator_allowlist=params.rule_generator_allowlist,
        environments=params.environments,
    )
    for cid in all_ids:
        inspect_case(state, cid)

    # ── Step 2b: pull in earlier cases of terminal violations ───────────────
    # Must run before the counters below are read, since it inspects more cases.
    expand_to_related_cases(state)
    _log_inspection_summary(state)

    last_case_timestamp = state.last_case_timestamp
    new_checkpoint = last_case_timestamp + 1 if last_case_timestamp else unix_now()
    _save_checkpoint_timestamp(siemplify, new_checkpoint)

    # ── Step 3: determine terminal/non-terminal status per violation ────────
    violation_status = resolve_violation_statuses(state)

    # ── Step 4: decide + apply per-case closure ──────────────────────────────
    counts = decide_and_apply_case_closures(state, violation_status, params.closure)
    _finish_run(siemplify, counts, params.closure.dry_run)


if __name__ == "__main__":
    main()
