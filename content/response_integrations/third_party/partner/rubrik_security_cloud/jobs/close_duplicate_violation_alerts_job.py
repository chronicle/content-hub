# Rubrik Security Cloud - Close Duplicate Violation Alerts Job
#
# Problem: RSC pushes a webhook event on every violation status transition
# ({Severity}SeverityDataViolation{Detected,InProgress,ReOpen,Remediated,
# Closed,Dismissed}). SecOps alerts are immutable after ingestion, so a
# playbook-driven status update (e.g. "Update DSPM Violation Status ->
# Remediated") gets echoed back by RSC as a brand-new duplicate alert for
# the same violation. This job cleans those duplicates up: it groups open
# cases' Rubrik alerts by violation series_id (custom_details.seriesId),
# finds the latest status-carrying alert per series_id, and if that status
# is terminal (Remediated/Closed/Dismissed), closes every case touched by
# that series_id -- unless a case also holds a *different*, still-open
# series_id, in which case it is left alone (see _decide_case_closures).
#
# See rsc-dspm/CLOSE_DUPLICATE_VIOLATION_ALERTS_JOB_PLAN.md for the full
# design writeup and rsc-dspm/CLOSE_DUPLICATE_VIOLATION_ALERTS_JOB_TEST_PLAN.md
# for the functional test plan.

from __future__ import annotations

import re
from datetime import datetime, timezone

from soar_sdk.ScriptResult import EXECUTION_STATE_COMPLETED
from soar_sdk.SiemplifyDataModel import (
    CaseFilterOperatorEnum,
    CaseFilterSortByEnum,
    CaseFilterSortOrderEnum,
)
from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler, unix_now

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


# Case status integer returned by `_get_case_by_id` for OPEN cases (matches
# the constant already used by the DRP Deduplication Job for the same SDK).
STATUS_OPEN = 1

# Event names that are audit/configuration events, not violation lifecycle
# events. IdentityAlertRuleCreated/Updated fire when
# an Identity Alert *rule* (policy) is added/edited -- their seriesId is a
# rule ID, not a violation ID, so they must never be folded into a
# violation's group.
AUDIT_OR_RULE_EVENT_NAMES = {
    "IdentityAlertRuleCreated",
    "IdentityAlertRuleUpdated",
}

# Matches the trailing status word off an RSC eventName, e.g.
# "HighSeverityDataViolationRemediated" -> "Remediated",
# "CriticalSeverityIdentityAlertDetected" -> "Detected".
# Anchored at the end so operational/export events like
# "DataViolationExportActionsLogRemediationSuccess" (ends in "Success", not
# "Remediated") correctly produce no match.
_STATUS_SUFFIX_RE = re.compile(
    r"(Detected|InProgress|ReOpen|Remediated|Closed|Dismissed)$"
)

TERMINAL_STATUSES = {"Remediated", "Closed", "Dismissed"}
NON_TERMINAL_STATUSES = {"Detected", "InProgress", "ReOpen"}

# (the dot is part of the literal key string, not a nested path) inside
# a security_event's `additional_properties` bag, e.g.:
#   alert["security_events"][0]["additional_properties"]["custom_details.eventName"]
#   alert["security_events"][0]["additional_properties"]["custom_details.seriesId"]
# Kept as ordered lists (first match wins) with a couple of casing/legacy
# fallbacks in case a different ingestion path (e.g. an older connector
# version) populates them differently.
_EVENT_NAME_KEYS = ("custom_details.eventName", "eventName", "EventName", "event_name")
_SERIES_ID_KEYS = (
    "custom_details.seriesId",
    "seriesId",
    "SeriesId",
    "series_id",
    "violation_id",
    "ViolationId",
)
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

    _validate_job_params(siemplify, max_cases=max_cases, lookback_days=lookback_days)
    
    if rule_generator_allowlist:
        siemplify.LOGGER.info(
            "Scoping to rule_generator in {}".format(rule_generator_allowlist)
        )
    else:
        siemplify.LOGGER.info(
            "No Rule Generator filter configured -- processing alerts across ALL open "
            "cases in the lookback window. Non-Rubrik alerts are naturally excluded "
            "because they won't yield an extractable series_id."
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
    lookback_ms = unix_now() - int(lookback_days) * MS_PER_DAY
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
    # series_id -> list of {"case_id", "alert_identifier", "event_name",
    #                        "timestamp", "status_suffix"}
    alerts_by_series = {}
    skipped_audit_rule_events = 0
    skipped_no_event_name = 0
    skipped_no_series_id = 0
    inspected_cases = 0

    for cid in all_ids:
        try:
            full_case = siemplify._get_case_by_id(str(cid))
        except Exception as e:
            siemplify.LOGGER.info("Could not fetch case {}: {}".format(cid, e))
            continue

        if full_case.get("status") != STATUS_OPEN:
            siemplify.LOGGER.info(
                "Fetched case {} but its status is not OPEN. SOAR filter anomaly or "
                "concurrent close? Skipping.".format(cid)
            )
            continue

        case_creation_time = full_case.get("creation_time", 0)
        alerts = full_case.get("cyber_alerts", []) or []
        matched_this_case = False

        for alert in alerts:
            rg = (alert.get("rule_generator") or "").strip()
            if rule_generator_allowlist and rg not in rule_generator_allowlist:
                continue

            event_name = _extract_event_name(alert)
            if not event_name:
                skipped_no_event_name += 1
                continue

            if event_name in AUDIT_OR_RULE_EVENT_NAMES:
                # Confirmed: seriesId on these does not represent a violation.
                skipped_audit_rule_events += 1
                continue

            series_id = _extract_series_id(alert)
            if not series_id:
                skipped_no_series_id += 1
                continue

            alert_identifier = alert.get("identifier")
            if not alert_identifier:
                continue

            timestamp = alert.get("creation_time") or case_creation_time

            alerts_by_series.setdefault(series_id, []).append({
                "case_id": str(cid),
                "alert_identifier": alert_identifier,
                "event_name": event_name,
                "timestamp": timestamp,
                "status_suffix": _parse_status_suffix(event_name),
            })
            matched_this_case = True

        if matched_this_case:
            inspected_cases += 1

    siemplify.LOGGER.info(
        "Inspected {} open case(s) with matching Rubrik alerts. Found {} distinct "
        "violation series_id(s). Skipped: {} audit/rule event(s), {} alert(s) with no "
        "extractable EventName, {} alert(s) with no extractable series_id.".format(
            inspected_cases,
            len(alerts_by_series),
            skipped_audit_rule_events,
            skipped_no_event_name,
            skipped_no_series_id,
        )
    )

    # ── Step 3: determine terminal/non-terminal status per series_id ────────
    series_status = {}  # series_id -> (is_terminal, latest_event_name, latest_timestamp)
    for series_id, records in alerts_by_series.items():
        status_records = [r for r in records if r["status_suffix"]]
        if not status_records:
            series_status[series_id] = (False, None, None)
            continue
        status_records.sort(key=lambda r: r["timestamp"])
        latest = status_records[-1]
        is_terminal = latest["status_suffix"] in TERMINAL_STATUSES
        series_status[series_id] = (is_terminal, latest["event_name"], latest["timestamp"])

    # ── Step 4: decide + apply per-case closure ──────────────────────────────
    closed_count, skipped_mixed_count, failed_count = _decide_and_apply_case_closures(
        siemplify=siemplify,
        alerts_by_series=alerts_by_series,
        series_status=series_status,
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

    `alert["security_events"][i]["additional_properties"]` holds FLAT keys
    with the literal dot in the name -- `"custom_details.eventName"` /
    `"custom_details.seriesId"` -- not a nested `custom_details` dict.
    """
    for event in alert.get("security_events") or []:
        props = event.get("additional_properties")
        if props:
            yield props


def _extract_event_name(alert):
    """Extraction of the RSC eventName mapped onto this alert.
    `security_events[i].additional_properties["custom_details.eventName"]`.
    Falls back to the alert-level additional-properties bag and a couple
    of plausible top-level keys for older/alternate ingestion paths.
    """
    for props in _iter_event_additional_properties(alert):
        for key in _EVENT_NAME_KEYS:
            value = props.get(key)
            if value:
                return value

    props = alert.get("additional_properties") or {}
    for key in _EVENT_NAME_KEYS:
        value = props.get(key)
        if value:
            return value
    for key in _EVENT_NAME_KEYS:
        value = alert.get(key)
        if value:
            return value
    return ""


def _extract_series_id(alert):
    """Extraction of the violation series_id for this alert.

    `security_events[i].additional_properties["custom_details.seriesId"]`.
    Falls back to the GenericEntity mapping (per the TDD's Ontology
    Mapping section) and the alert-level additional-properties bag for
    older/alternate ingestion paths.
    """
    for props in _iter_event_additional_properties(alert):
        for key in _SERIES_ID_KEYS:
            value = props.get(key)
            if value:
                return str(value).strip()

    for entity in alert.get("entities") or []:
        entity_type = (entity.get("entity_type") or entity.get("type") or "").strip().lower()
        if entity_type in _GENERIC_ENTITY_TYPES:
            identifier = (entity.get("identifier") or "").strip()
            if identifier:
                return identifier

    props = alert.get("additional_properties") or {}
    for key in _SERIES_ID_KEYS:
        value = props.get(key)
        if value:
            return str(value).strip()

    return ""


def _parse_status_suffix(event_name):
    """Return the trailing status word of an RSC eventName, or None if the
    eventName doesn't end in a recognized status word (e.g. an operational
    event like DataViolationExportActionsLogRemediationSuccess, or the IR
    audit echo IdentityViolationStatusUpdated)."""
    match = _STATUS_SUFFIX_RE.search(event_name or "")
    return match.group(1) if match else None


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
    alerts_by_series,
    series_status,
    close_root_cause,
    close_reason,
    comment_prefix,
    dry_run,
):
    """Close every case whose Rubrik alerts belong ONLY to series_id groups
    that have all reached a terminal status. A case that also holds a
    different, still-open series_id is left alone entirely -- closing the
    whole case would incorrectly close an unrelated, still-active
    violation that happens to share the case.

    Returns (closed_count, skipped_mixed_count, failed_count).
    """
    case_to_series = {}
    for series_id, records in alerts_by_series.items():
        for record in records:
            case_to_series.setdefault(record["case_id"], set()).add(series_id)

    closed_count = 0
    skipped_mixed_count = 0
    failed_count = 0

    for case_id, series_ids in case_to_series.items():
        statuses = {sid: series_status[sid] for sid in series_ids}
        non_terminal = [sid for sid, (is_terminal, _, _) in statuses.items() if not is_terminal]

        if non_terminal:
            if len(series_ids) > 1:
                siemplify.LOGGER.info(
                    "Case {}: skipping -- contains {} still-open violation series_id(s) "
                    "alongside {} terminal one(s). Leaving case open.".format(
                        case_id, len(non_terminal), len(series_ids) - len(non_terminal)
                    )
                )
                skipped_mixed_count += 1
            # else: the single violation in this case simply isn't terminal yet
            # -- expected, not worth a log line per case on every run.
            continue

        # Every series_id touching this case is terminal -> close it.
        records_in_case = [
            r for sid in series_ids for r in alerts_by_series[sid] if r["case_id"] == case_id
        ]
        representative_alert_id = records_in_case[0]["alert_identifier"]

        breakdown_lines = "\n".join(
            "  - series_id={}: latest event={} at {}".format(
                sid, statuses[sid][1], _format_timestamp(statuses[sid][2])
            )
            for sid in sorted(series_ids)
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
                "[DRY RUN] Would add comment and close case {} ({} alert(s), series_id(s) "
                "{}).".format(case_id, len(records_in_case), sorted(series_ids))
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
                "Closed case {} ({} alert(s), series_id(s) {}).".format(
                    case_id, len(records_in_case), sorted(series_ids)
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


def _verify_status_with_rsc(manager, series_id, policy_types):
    """Extension point (NOT implemented in v1, NOT called from main()).

    Would call APIManager.get_ir_violation_details / get_dspm_violation_details
    to double-check a violation's live status directly against RSC instead of
    trusting the last-ingested webhook payload's EventName. See the plan
    doc's "Status detection: v1 vs. future enhancement" section for why this
    isn't expected to be necessary -- the webhook is the authoritative source.
    """
    raise NotImplementedError(
        "Verify Status Via RSC API is not implemented in v1. See "
        "rsc-dspm/CLOSE_DUPLICATE_VIOLATION_ALERTS_JOB_PLAN.md."
    )


if __name__ == "__main__":
    main()
