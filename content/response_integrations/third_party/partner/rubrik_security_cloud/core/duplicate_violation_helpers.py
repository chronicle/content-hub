"""Case-inspection and duplicate-resolution helpers for the Close Duplicate
Violation Alerts job.

The job groups open cases' Rubrik alerts per violation (by activitySeriesId),
resolves each violation's latest status, and closes every case whose violations
have all reached a terminal status. The module header of
jobs/rubrik_security_cloud_close_duplicate_violation_alerts_job.py explains the
end-to-end flow; this module holds the per-step logic it drives.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from .constants import (
    RSC_FETCH_TYPE_DSPM,
    RSC_FETCH_TYPE_IR,
    TERMINAL_POLICY_VIOLATION_STATUSES,
)

if TYPE_CHECKING:
    from soar_sdk.SiemplifyJob import SiemplifyJob
    from TIPCommon.types import SingleJson

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
# extract_violation_id for why classification must be excluded.
_VIOLATION_TYPES = {RSC_FETCH_TYPE_DSPM, RSC_FETCH_TYPE_IR}

# Fallback source for the violation id: the GenericEntity the TDD's Ontology
# Mapping section uses to enforce case grouping by violation id. Kept so a case
# whose alert carries the id only as a mapped entity still groups correctly.
_GENERIC_ENTITY_TYPES = {"genericentity", "generic_entity", "generic entity"}


@dataclass
class DedupRunState:
    """State shared by Steps 2-4 of one job run.

    Attributes:
        siemplify: The running SiemplifyJob.
        rule_generator_allowlist: "Rule Generator" param values; empty = no filter.
        environments: "Environment" param values, or None for no filter.
        alerts_by_violation: violation id -> list of {"case_id",
            "alert_identifier", "event_name", "timestamp", "status", "alert_name"}.
        inspected_ids: Case ids already fetched this run. Guards against fetching
            a case twice, which would double-count its alerts within a group.
        skipped_no_violation_id: Alerts skipped for carrying no violation id.
        inspected_cases: Cases that contributed at least one matching alert.
        last_case_timestamp: Newest modification/creation time seen, or None.
    """

    siemplify: SiemplifyJob
    rule_generator_allowlist: list[str]
    environments: list[str] | None
    alerts_by_violation: dict[str, list[SingleJson]] = field(default_factory=dict)
    inspected_ids: set[str] = field(default_factory=set)
    skipped_no_violation_id: int = 0
    inspected_cases: int = 0
    last_case_timestamp: int | None = None


@dataclass
class ClosureOptions:
    """The job params that shape how Step 4 closes a case."""

    close_root_cause: str
    close_reason: str
    comment_prefix: str
    dry_run: bool


@dataclass
class ClosureCounts:
    """Step 4's tallies, reported in the job's summary message."""

    closed: int = 0
    skipped_mixed: int = 0
    failed: int = 0


@dataclass
class _ExpansionProgress:
    """Step 2b's running tallies across the alert names it searches."""

    found: int = 0
    inspected: int = 0
    budget_exhausted: bool = False


def _iter_event_additional_properties(alert: SingleJson) -> Iterator[SingleJson]:
    """Yield each `additional_properties` dict off this alert's security_events.

    `alert["security_events"][i]["additional_properties"]` holds the flat event
    fields the connector ingested, keyed by the connector's own field names.
    """
    for event in alert.get("security_events") or []:
        props = event.get("additional_properties")
        if props:
            yield props


def _extract_event_field(alert: SingleJson, field_names: tuple[str, ...]) -> str:
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


def inspect_case(state: DedupRunState, cid: int | str) -> bool:
    """Fetch one open case and fold its Rubrik alerts into alerts_by_violation.

    Shared by Step 2 (the checkpoint window) and Step 2b (a violation's other
    cases, found by case name). Both must extract identically -- if Step 2b
    grouped or read status differently, a violation's alerts would split across
    two groups and neither would resolve correctly.

    `state` is mutated in place: skipped_no_violation_id, inspected_cases and
    last_case_timestamp. `state.inspected_ids` guards against fetching a case
    twice, which would double-count its alerts within a violation group.

    Returns:
        True if the case was fetched and inspected, False if it was skipped
        (already seen, unfetchable, or no longer OPEN).
    """
    siemplify = state.siemplify
    case_id = str(cid)
    if case_id in state.inspected_ids:
        return False
    state.inspected_ids.add(case_id)

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

    state.last_case_timestamp = max(
        state.last_case_timestamp or 0,
        full_case.get("modification_time") or full_case.get("creation_time", 0),
    )

    if _fold_case_alerts(state, case_id, full_case):
        state.inspected_cases += 1
    return True


def _fold_case_alerts(state: DedupRunState, case_id: str, full_case: SingleJson) -> bool:
    """Append each matching Rubrik alert of `full_case` to its violation group.

    Returns:
        True if at least one alert of this case was added to a group.
    """
    case_creation_time = full_case.get("creation_time", 0)
    alerts = full_case.get("cyber_alerts", []) or []
    matched_this_case = False

    for alert in alerts:
        if state.rule_generator_allowlist and not matches_rule_generator(
            alert, state.rule_generator_allowlist
        ):
            continue

        violation_id = extract_violation_id(alert)
        if not violation_id:
            state.skipped_no_violation_id += 1
            continue

        alert_identifier = alert.get("identifier")
        if not alert_identifier:
            continue

        timestamp = alert.get("creation_time") or case_creation_time

        state.alerts_by_violation.setdefault(violation_id, []).append({
            "case_id": case_id,
            "alert_identifier": alert_identifier,
            "event_name": _extract_event_field(alert, _EVENT_NAME_KEYS),
            "timestamp": timestamp,
            "status": _extract_event_field(alert, _STATUS_KEYS),
            "alert_name": _extract_event_field(alert, _ALERT_NAME_KEYS),
        })
        matched_this_case = True

    return matched_this_case


def latest_status_record(records: list[SingleJson]) -> SingleJson | None:
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


def expand_to_related_cases(state: DedupRunState) -> None:
    """Pull in the earlier cases of every violation that has reached a terminal status.

    This is the fix for the 24-hour grouping window. A violation detected on day 0
    and remediated on day 4 raises its terminal alert into a NEW case, because the
    grouping identifier only merges alerts within 24 hours. The original case is
    left holding an IN_PROGRESS alert as its newest, and the checkpoint means it is
    never re-fetched -- so it stays open forever.

    Only terminal violations are expanded: a violation still in progress has
    nothing to close, so searching for its other cases would be wasted calls.

    Newly found cases are inspected through inspect_case, i.e. their alerts join
    the SAME violation groups. That is what makes the fix work without a second
    closing path: Step 3 then sees the terminal alert from the new case and the
    stale one from the old case in one group and resolves the violation as
    terminal, and Step 4's existing "every violation in this case must be
    terminal" guard still protects a case that also holds unrelated open work.

    Mutates `state` in place; the caller reads the outcome from it, so nothing is
    returned.
    """
    siemplify = state.siemplify
    if MAX_RELATED_CASES_TO_INSPECT <= 0:
        siemplify.LOGGER.info(
            "MAX_RELATED_CASES_TO_INSPECT is 0. Skipping the related-case expansion; "
            "cases opened outside the 24h grouping window will not be closed."
        )
        return

    names_to_search = _collect_terminal_alert_names(state.alerts_by_violation)

    if not names_to_search:
        siemplify.LOGGER.info(
            "No violation reached a terminal status this run. Nothing to expand."
        )
        return

    siemplify.LOGGER.info(
        "Searching {} distinct alert name(s) for earlier cases of terminal "
        "violations.".format(len(names_to_search))
    )

    progress = _search_related_cases(state, names_to_search)
    _log_expansion_summary(siemplify, progress, len(names_to_search))


def _search_related_cases(state: DedupRunState, names_to_search: set[str]) -> _ExpansionProgress:
    """Search each name in sorted order until MAX_RELATED_CASES_TO_INSPECT is hit."""
    progress = _ExpansionProgress()
    for alert_name in sorted(names_to_search):
        _inspect_related_cases_for_name(state, progress, alert_name)
        if progress.budget_exhausted:
            break
    return progress


def _collect_terminal_alert_names(
    alerts_by_violation: dict[str, list[SingleJson]],
) -> set[str]:
    """Distinct alert names of every violation whose latest status is terminal."""
    # Group by name, not by violation: many violations share an alert name (same
    # policy, same object), and one lookup per distinct name collapses the calls.
    names_to_search = set()
    for records in alerts_by_violation.values():
        latest = latest_status_record(records)
        if not latest or latest["status"] not in TERMINAL_POLICY_VIOLATION_STATUSES:
            continue
        for record in records:
            if record["alert_name"]:
                names_to_search.add(record["alert_name"])
    return names_to_search


def _inspect_related_cases_for_name(
    state: DedupRunState,
    progress: _ExpansionProgress,
    alert_name: str,
) -> None:
    """Search one alert name and inspect its not-yet-seen cases, within budget."""
    candidate_ids = _find_related_case_ids(state, alert_name)
    # Already-inspected ids are the common case, not an anomaly: the case that
    # produced this name in Step 2 matches its own name search.
    new_ids = [cid for cid in candidate_ids if cid not in state.inspected_ids]
    progress.found += len(new_ids)
    # Both counts, because they fail for opposite reasons: 0 matched means the
    # filter itself found nothing (name, status, environment or response shape),
    # while matched>0 with new=0 means the filter works and the only case
    # bearing this name is one already inspected this run.
    state.siemplify.LOGGER.info(
        "Name {!r}: {} case(s) matched the filter, {} of them not yet "
        "inspected. Matched ids: {}".format(
            alert_name, len(candidate_ids), len(new_ids), candidate_ids
        )
    )

    for cid in new_ids:
        if progress.inspected >= MAX_RELATED_CASES_TO_INSPECT:
            progress.budget_exhausted = True
            break
        if inspect_case(state, cid):
            progress.inspected += 1


def _log_expansion_summary(
    siemplify: SiemplifyJob,
    progress: _ExpansionProgress,
    names_searched: int,
) -> None:
    """Log Step 2b's outcome, including any cases left for the next run."""
    if progress.budget_exhausted:
        siemplify.LOGGER.info(
            "Hit MAX_RELATED_CASES_TO_INSPECT ({}). {} further related case(s) were "
            "found but NOT inspected this run -- the next run picks them up.".format(
                MAX_RELATED_CASES_TO_INSPECT, progress.found - progress.inspected
            )
        )

    siemplify.LOGGER.info(
        "Related-case expansion: {} name(s) searched, {} previously-unseen case(s) "
        "found, {} inspected. Cases whose alerts belong to a different violation are "
        "grouped separately and left alone.".format(
            names_searched, progress.found, progress.inspected
        )
    )


def _find_related_case_ids(state: DedupRunState, alert_name: str) -> list[str]:
    """Case ids of other OPEN cases whose case name is `alert_name`.

    SecOps groups alerts into one case only within a 24-hour window, so a
    violation that is remediated days after it was detected raises its terminal
    alert into a BRAND NEW case. The original case's newest alert still reads
    IN_PROGRESS and the checkpoint guarantees it is never re-fetched, so without
    this lookup it stays open forever.

    A name match is only a candidate: distinct violations of the same policy on
    the same object share a name. The caller confirms identity by activitySeriesId.

    Returns:
        A list of case ids, or [] if the lookup failed -- a failure must not stop
        the run, it only leaves those cases unclosed until a later run retries.
    """
    siemplify = state.siemplify
    try:
        response = _search_open_cases_by_name(state, alert_name)
    except Exception as e:
        siemplify.LOGGER.error(
            "Related-case lookup failed for alert name {!r}: {}".format(alert_name, e)
        )
        return []

    case_ids = normalize_case_ids(response)
    if not case_ids:
        # An empty result and an unrecognised envelope are indistinguishable from
        # the count alone, and normalize_case_ids returns [] for both. Show the
        # raw payload so a shape mismatch cannot masquerade as "no matches".
        siemplify.LOGGER.info(
            "Name search for {!r} yielded no case ids. Raw response type={}, "
            "value={}".format(
                alert_name, type(response).__name__, str(response)[:500]
            )
        )
    return case_ids


def _search_open_cases_by_name(state: DedupRunState, alert_name: str) -> object:
    """Run the get_cases_by_filter search for OPEN cases named `alert_name`.

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

    `environments` is the same filter Step 1 uses. It must be applied here too --
    otherwise the Environment param would scope which cases are inspected but not
    which ones this step drags back in, and the job would close cases in
    environments it was explicitly told to leave alone.

    Returns:
        The raw SDK response (json.loads of the body), in whatever shape it has.
    """
    return state.siemplify.get_cases_by_filter(
        case_names=[alert_name],
        statuses=[CASE_STATUS_FILTER_OPEN],
        environments=state.environments,
    )


def normalize_case_ids(response: object) -> list[str]:
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


def extract_violation_id(alert: SingleJson) -> str:
    """Extract the id of the RSC violation this alert belongs to.

    Always the activitySeriesId: it is on every DSPM/IR alert, is shared by all of
    one violation's alerts, and is what the connector sets as the case grouping
    identifier -- so grouping on it here lands on the same set of alerts the case
    does. policyViolationId is not consulted at all; see the _SERIES_ID_KEYS notes.

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


def matches_rule_generator(alert: SingleJson, rule_generator_allowlist: list[str]) -> bool:
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


def resolve_violation_statuses(state: DedupRunState) -> dict[str, SingleJson]:
    """Step 3: determine terminal/non-terminal status per violation.

    Returns:
        violation id -> {"is_terminal", "status", "timestamp", "event_name"}
    """
    # Every transition of a violation is its own immutable alert, so the newest
    # status-carrying alert holds the violation's current state. Alerts with no
    # status at all are ignored for this decision rather than treated as open --
    # otherwise one unresolvable alert would pin an otherwise-remediated
    # violation open forever.
    violation_status = {}
    no_status_violations = 0
    for violation_id, records in state.alerts_by_violation.items():
        latest = latest_status_record(records)
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
    state.siemplify.LOGGER.info(
        "Violation statuses resolved: {} terminal, {} still open, {} with no status "
        "field on any alert (left open).".format(
            terminal_count,
            len(violation_status) - terminal_count - no_status_violations,
            no_status_violations,
        )
    )
    return violation_status


def _format_timestamp(timestamp_ms: int | str | None) -> str:
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


@dataclass
class _ClosureRun:
    """Everything Step 4 shares across the cases it decides on."""

    state: DedupRunState
    options: ClosureOptions
    counts: ClosureCounts = field(default_factory=ClosureCounts)


@dataclass
class _CaseToClose:
    """One case whose every violation has reached a terminal status."""

    case_id: str
    violation_ids: set[str]
    statuses: dict[str, SingleJson]
    records_in_case: list[SingleJson]

    @property
    def representative_alert_id(self) -> str:
        """The alert the case-level comment/close calls are attributed to."""
        return self.records_in_case[0]["alert_identifier"]


def decide_and_apply_case_closures(
    state: DedupRunState,
    violation_status: dict[str, SingleJson],
    options: ClosureOptions,
) -> ClosureCounts:
    """Close every case whose Rubrik alerts belong ONLY to violation groups
    that have all reached a terminal status. A case that also holds a
    different, still-open violation is left alone entirely -- closing the
    whole case would incorrectly close an unrelated, still-active
    violation that happens to share the case.

    Returns the closed, skipped-mixed and failed case counts.
    """
    case_to_violations = {}
    for violation_id, records in state.alerts_by_violation.items():
        for record in records:
            case_to_violations.setdefault(record["case_id"], set()).add(violation_id)

    run = _ClosureRun(state=state, options=options)
    for case_id, violation_ids in case_to_violations.items():
        statuses = {vid: violation_status[vid] for vid in violation_ids}
        if not _all_violations_terminal(run, case_id, statuses):
            continue

        # Every violation touching this case is terminal -> close it.
        records_in_case = [
            r for vid in violation_ids for r in state.alerts_by_violation[vid] if r["case_id"] == case_id
        ]
        _close_case(run, _CaseToClose(case_id, violation_ids, statuses, records_in_case))

    return run.counts


def _all_violations_terminal(
    run: _ClosureRun,
    case_id: str,
    statuses: dict[str, SingleJson],
) -> bool:
    """Whether every violation in this case is terminal. A case holding a
    still-open violation alongside terminal ones is logged and counted as a
    mixed skip."""
    violation_ids = statuses.keys()
    non_terminal = [vid for vid, state in statuses.items() if not state["is_terminal"]]

    if non_terminal:
        if len(violation_ids) > 1:
            run.state.siemplify.LOGGER.info(
                "Case {}: skipping -- contains {} still-open violation(s) "
                "alongside {} terminal one(s). Leaving case open.".format(
                    case_id, len(non_terminal), len(violation_ids) - len(non_terminal)
                )
            )
            run.counts.skipped_mixed += 1
        # else: the single violation in this case simply isn't terminal yet
        # -- expected, not worth a log line per case on every run.
        return False
    return True


def _build_case_comment(case: _CaseToClose, comment_prefix: str) -> str:
    """The case comment explaining why this case is being auto-closed."""
    statuses = case.statuses
    breakdown_lines = "\n".join(
        "  - violation {}: latest status={} (event={}) at {}".format(
            vid,
            statuses[vid]["status"],
            statuses[vid]["event_name"] or "N/A",
            _format_timestamp(statuses[vid]["timestamp"]),
        )
        for vid in sorted(case.violation_ids)
    )
    return (
        "{prefix} Attempting to auto-close this case -- every Rubrik violation in it "
        "has reached a terminal status in RSC:\n{breakdown}\n"
        "Closing {n} matching alert(s) in this case.".format(
            prefix=comment_prefix,
            breakdown=breakdown_lines,
            n=len(case.records_in_case),
        )
    )


def _close_case(run: _ClosureRun, case: _CaseToClose) -> None:
    """Comment on and close one fully-terminal case (or just log it on a dry run)."""
    case_id = case.case_id
    case_comment = _build_case_comment(case, run.options.comment_prefix)
    if run.options.dry_run:
        run.state.siemplify.LOGGER.info(
            "[DRY RUN] Would add comment and close case {} ({} alert(s), "
            "violation(s) {}).".format(
                case_id, len(case.records_in_case), sorted(case.violation_ids)
            )
        )
        run.counts.closed += 1
        return

    try:
        _apply_case_closure(run, case, case_comment)
        run.counts.closed += 1
    except Exception as e:
        run.counts.failed += 1
        _report_closure_failure(run, case, e)


def _apply_case_closure(run: _ClosureRun, case: _CaseToClose, case_comment: str) -> None:
    """Add the explanatory comment, close the case and log it. Raises on failure."""
    siemplify = run.state.siemplify
    options = run.options
    case_id = case.case_id
    representative_alert_id = case.representative_alert_id
    close_comment = "{} Duplicate/stale violation alert(s) -- see case comment.".format(
        options.comment_prefix
    )

    siemplify.add_comment(case_comment, case_id, representative_alert_id)
    siemplify.close_case(
        root_cause=options.close_root_cause,
        comment=close_comment,
        reason=options.close_reason,
        case_id=case_id,
        alert_identifier=representative_alert_id,
    )
    siemplify.LOGGER.info(
        "Closed case {} ({} alert(s), violation(s) {}).".format(
            case_id, len(case.records_in_case), sorted(case.violation_ids)
        )
    )


def _report_closure_failure(run: _ClosureRun, case: _CaseToClose, error: Exception) -> None:
    """Log a failed closure and best-effort leave a failure comment on the case."""
    siemplify = run.state.siemplify
    case_id = case.case_id
    representative_alert_id = case.representative_alert_id
    failure_comment = (
        "{} Failed to auto-close this case -- see job logs for details.".format(
            run.options.comment_prefix
        )
    )
    siemplify.LOGGER.error("Failed to close case {}: {}".format(case_id, error))
    try:
        siemplify.add_comment(failure_comment, case_id, representative_alert_id)
    except Exception as comment_err:
        siemplify.LOGGER.error(
            "Additionally failed to add failure comment to case {}: {}".format(
                case_id, comment_err
            )
        )
