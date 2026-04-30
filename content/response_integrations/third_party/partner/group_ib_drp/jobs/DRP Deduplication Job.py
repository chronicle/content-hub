# DRP Violation Deduplication Job
# Scheduled job that reconciles open DRP cases sharing the same violation UID.
#
# Merge Mode:
#   - "merge" (default): POST /v1beta/.../cases:merge. Folds the duplicate's
#                        alerts, comments, tags, and entities into the primary
#                        and removes the duplicate. IAM: chronicle.cases.update.
#                        Docs: https://docs.cloud.google.com/chronicle/docs/reference/rest/v1beta/projects.locations.instances.cases/merge
#   - "close":           close_case + back-reference comment. Optional
#                        Carry Over To Primary copies analyst comments/tags/
#                        entities to the primary before close.

from __future__ import annotations

import re

from soar_sdk.SiemplifyJob import SiemplifyJob
from soar_sdk.SiemplifyUtils import output_handler, unix_now

SCRIPT_NAME = "DRP-Deduplication-Job"

# Merge Mode values
MERGE_MODE_CLOSE = "close"
MERGE_MODE_MERGE = "merge"
MERGE_MODE_VALUES = {MERGE_MODE_CLOSE, MERGE_MODE_MERGE}

# Matches the 'projects/<p>/locations/<l>/instances/<i>' segment inside a URL.
_INSTANCE_PATH_RE = re.compile(r"projects/[^/]+/locations/[^/]+/instances/[^/]+")

# If sdk_config's URL template embeds these literals, the SOAR runtime didn't
# populate the one-platform env vars on this worker and auto-detection has to
# fail out so we don't POST to a placeholder URL.
_SDK_CONFIG_FALLBACK_TOKENS = (
    "/projects/project/",
    "/locations/location/",
    "/instances/instance/",
)

# Case status integer returned by `_get_case_by_id` for OPEN cases.
#
# Note on `_get_case_by_id`: at the time of writing the soar_sdk
# (`Siemplify.py`) does not expose a public method that returns a case's
# full details (status, creation_time, cyber_alerts, …). The closest
# public helpers (`get_cases_by_filter`, `get_sync_cases`) return only
# summary rows that lack `cyber_alerts`, which the dedup job needs to
# match `rule_generator` and `ticket_id` per alert. Until a public
# equivalent ships we deliberately call the leading-underscore method
# below; the call is isolated and wrapped in a try/except so any future
# breakage stays scoped.
STATUS_OPEN = 1

MS_PER_DAY = 24 * 60 * 60 * 1000


@output_handler
def main() -> None:
    """Deduplicate DRP cases that share the same violation UID.

    Job pipeline:

    1. Read job parameters (case type, lookback window, max cases, dry-run
       flag, optional global merge URL).
    2. Use ``get_cases_ids_by_filter`` to enumerate OPEN case IDs within the
       lookback window (capped to ``Max Cases To Process``).
    3. Fetch each case's full payload (``_get_case_by_id``) and group cases
       by violation UID, taking the earliest case as the "primary" survivor.
    4. For every duplicate, copy entities/comments/tags onto the primary,
       then close the duplicate via the SOAR REST API. In dry-run mode the
       same plan is logged but no mutating call is made.
    5. Emit a structured run summary (counts of merged cases, copied
       entities, errors) before exiting.
    """
    siemplify = SiemplifyJob()
    siemplify.script_name = SCRIPT_NAME
    siemplify.LOGGER.info("=== DRP Deduplication Job started ===")

    # ── Read job parameters from SOAR UI ────────────────────────────────────
    case_type = siemplify.extract_job_param(
        param_name="Case Type",
        is_mandatory=True,
        print_value=True,
    )
    max_cases = siemplify.extract_job_param(
        param_name="Max Cases To Process",
        input_type=int,
        is_mandatory=True,
        print_value=True,
    )
    lookback_days = siemplify.extract_job_param(
        param_name="Lookback Days",
        input_type=int,
        default_value=30,
        is_mandatory=False,
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
        default_value="Duplicate",
        is_mandatory=False,
        print_value=True,
    )
    close_reason = siemplify.extract_job_param(
        param_name="Close Reason",
        default_value="Maintenance",
        is_mandatory=False,
        print_value=True,
    )
    carry_over = siemplify.extract_job_param(
        param_name="Carry Over To Primary",
        input_type=bool,
        default_value=False,
        is_mandatory=False,
        print_value=True,
    )
    merge_mode_raw = siemplify.extract_job_param(
        param_name="Merge Mode",
        default_value=MERGE_MODE_MERGE,
        is_mandatory=False,
        print_value=True,
    )
    # Optional manual override; blank on healthy tenants (auto-detected from
    # sdk_config). Populate only if startup logs "could not auto-detect"; the
    # "DRP: Get Chronicle Instance Path" action prints the expected value.
    chronicle_instance_path = siemplify.extract_job_param(
        param_name="Chronicle Instance Path",
        default_value="",
        is_mandatory=False,
        print_value=True,
    )
    merge_mode = (merge_mode_raw or MERGE_MODE_MERGE).strip().lower()
    if merge_mode not in MERGE_MODE_VALUES:
        siemplify.LOGGER.error(
            "Unrecognised Merge Mode {!r}. Accepted: {}. Falling back to 'merge'.".format(
                merge_mode_raw, sorted(MERGE_MODE_VALUES)
            )
        )
        merge_mode = MERGE_MODE_MERGE

    if merge_mode == MERGE_MODE_MERGE and carry_over:
        siemplify.LOGGER.info(
            "Merge Mode is 'merge': Carry Over To Primary is redundant (cases.merge "
            "folds the duplicate's alerts, comments, tags, and entities into the "
            "primary by design). Ignoring the carry-over flag for this run."
        )
        carry_over = False

    # Resolve the cases:merge URL once up front so merge-mode fails fast with
    # one diagnostic instead of producing a 404 per duplicate.
    merge_url = None
    if merge_mode == MERGE_MODE_MERGE:
        merge_url, source = _resolve_merge_url(
            siemplify=siemplify,
            instance_path_override=chronicle_instance_path,
        )
        if not merge_url:
            siemplify.LOGGER.error(
                "Merge Mode is 'merge' but the cases:merge URL could not be "
                "auto-detected, and the 'Chronicle Instance Path' override is "
                "blank. Run the action 'DRP: Get Chronicle Instance Path' on "
                "any case, copy the reported 'projects/<P>/locations/<L>/"
                "instances/<I>' segment, and paste it into this job's "
                "'Chronicle Instance Path' parameter. Diagnostics: "
                "API_ROOT={!r}, one_platform_api_root_uri_format={!r}, "
                "Chronicle Instance Path override={!r}. Aborting.".format(
                    getattr(siemplify, "API_ROOT", None),
                    _safe_get_one_platform_format(siemplify),
                    chronicle_instance_path,
                )
            )
            siemplify.end_script()
            return
        siemplify.LOGGER.info("Resolved cases:merge URL via {}: {}".format(source, merge_url))

    # ── Step 1: fetch candidate case IDs ────────────────────────────────────
    # Use get_cases_ids_by_filter (10k cap) rather than get_cases_by_filter,
    # which silently caps at ~100.
    lookback_ms = unix_now() - int(lookback_days) * MS_PER_DAY
    try:
        all_ids = (
            siemplify.get_cases_ids_by_filter(
                status="OPEN",
                start_time_from_unix_time_in_ms=lookback_ms,
                max_results=10000,
            )
            or []
        )
    except Exception as e:
        siemplify.LOGGER.error("Failed to fetch case IDs: {}".format(e))
        raise

    # Defensive: dedupe the ID list in case the backend ever returns a
    # repeat. Preserves ordering.
    before_dedupe = len(all_ids)
    all_ids = list(dict.fromkeys(all_ids))
    if len(all_ids) != before_dedupe:
        siemplify.LOGGER.info("Deduplicated case ID list: {} → {} unique IDs.".format(before_dedupe, len(all_ids)))

    siemplify.LOGGER.info("Fetched {} open case IDs (lookback {} days).".format(len(all_ids), lookback_days))

    if len(all_ids) > max_cases:
        siemplify.LOGGER.info("Capping to {} cases (Max Cases To Process).".format(max_cases))
        all_ids = all_ids[:max_cases]

    # ── Step 2: fetch full cases and group by violation UID ─────────────────
    # Keep alerts whose rule_generator matches case_type exactly or as a
    # prefix ("Violations: example.com" — connectors embed the host so the
    # case title shows the URL). UID comes from alert.ticket_id, falling
    # back to alert.additional_properties.TicketId.

    uid_to_cases = {}
    inspected = 0
    status_dist = {}

    for cid in all_ids:
        try:
            full_case = siemplify._get_case_by_id(str(cid))
        except Exception as e:
            siemplify.LOGGER.warning("Could not fetch case {}: {}".format(cid, e))
            continue

        case_status_val = full_case.get("status")
        status_dist[case_status_val] = status_dist.get(case_status_val, 0) + 1

        # Layer-1 filter already asked for OPEN; surface any slip-through loudly.
        if case_status_val != STATUS_OPEN:
            siemplify.LOGGER.warn(
                "Fetched case {} has status {} but filter asked for OPEN ({}). "
                "SOAR filter anomaly or concurrent close? Skipping.".format(cid, case_status_val, STATUS_OPEN)
            )
            continue

        case_start_time = full_case.get("creation_time", 0)
        alerts = full_case.get("cyber_alerts", []) or []

        # Per-case UID dedup: a single case can hold multiple alerts with the
        # same ticket_id (platform-side grouping of re-ingests, or a prior
        # merge). Without this guard the case would register itself multiple
        # times under the same UID and then get treated as its own duplicate
        # in Step 3.
        uids_recorded_for_this_case = set()

        matched_this_case = False
        for alert in alerts:
            rg = (alert.get("rule_generator") or "").strip()
            if not (rg == case_type or rg.startswith(case_type + ":")):
                continue

            uid = alert.get("ticket_id") or alert.get("additional_properties", {}).get("TicketId", "")
            if not uid:
                continue

            alert_identifier = alert.get("identifier")
            if not alert_identifier:
                continue

            if uid in uids_recorded_for_this_case:
                continue
            uids_recorded_for_this_case.add(uid)

            uid_to_cases.setdefault(uid, []).append({
                "case_id": str(cid),
                "start_time": case_start_time,
                "alert_identifier": alert_identifier,
                "rule_generator": rg,
                # Stashed for optional carry-over to primary (close mode).
                "environment": full_case.get("environment"),
                "case_tags": list(full_case.get("tags", []) or []),
                "alert_tags": list(alert.get("tags", []) or []),
                "entities": list(alert.get("entities", []) or []),
            })
            matched_this_case = True

        if matched_this_case:
            inspected += 1

    siemplify.LOGGER.info("Status distribution across all fetched cases: {}".format(status_dist))
    siemplify.LOGGER.info(
        "Inspected {} DRP cases. Found {} distinct violation UIDs.".format(inspected, len(uid_to_cases))
    )

    if inspected == 0 and len(all_ids) > 0:
        siemplify.LOGGER.warn(
            "Inspected 0 DRP cases (rule_generator matching '{0}' or '{0}: ...') "
            "out of {1} fetched. Likely a mismatch between the job's Case Type "
            "param and the connector's Case type param.".format(case_type, len(all_ids))
        )

    # ── Step 3: reconcile duplicates (close OR merge, per Merge Mode) ───────
    closed_duplicates_count = 0
    merged_duplicates_count = 0
    failed_duplicates_count = 0
    skipped_count = 0
    self_pair_skipped = 0

    for uid, cases_list in uid_to_cases.items():
        if len(cases_list) < 2:
            skipped_count += 1
            continue

        # Primary case = oldest (lowest creation_time)
        cases_list.sort(key=lambda c: c["start_time"])
        primary = cases_list[0]
        duplicates = cases_list[1:]

        siemplify.LOGGER.info(
            "UID {}…: primary case {} has {} duplicate(s). Mode: {}".format(
                uid[:16], primary["case_id"], len(duplicates), merge_mode
            )
        )

        for dup in duplicates:
            # Safety net: never reconcile a case against itself.
            if dup["case_id"] == primary["case_id"]:
                siemplify.LOGGER.warning(
                    "Refusing self-reconcile: primary and duplicate both point "
                    "to case {} for UID {}…. Skipping.".format(primary["case_id"], uid[:16])
                )
                self_pair_skipped += 1
                continue

            if merge_mode == MERGE_MODE_MERGE:
                try:
                    did_merge = _merge_cases_v1beta(
                        siemplify=siemplify,
                        merge_url=merge_url,
                        primary_case_id=primary["case_id"],
                        duplicate_case_id=dup["case_id"],
                        duplicate_rule_generator=dup["rule_generator"],
                        uid=uid,
                        case_type=case_type,
                        dry_run=dry_run,
                    )
                    if did_merge:
                        merged_duplicates_count += 1
                except Exception as e:
                    failed_duplicates_count += 1
                    siemplify.LOGGER.error(
                        "Failed to merge duplicate case {} into primary {}: {}".format(
                            dup["case_id"], primary["case_id"], e
                        )
                    )
                continue

            # ── Close-mode path ────────────────────────────────────────────
            if carry_over:
                try:
                    _carry_over_to_primary(
                        siemplify=siemplify,
                        primary=primary,
                        duplicate=dup,
                        dry_run=dry_run,
                    )
                except Exception as e:
                    siemplify.LOGGER.warn(
                        "Carry-over from case {} to primary {} partially failed at "
                        "the outer level: {}. Proceeding to close.".format(dup["case_id"], primary["case_id"], e)
                    )

            try:
                did_close = _close_duplicate_with_reference(
                    siemplify=siemplify,
                    primary_case_id=primary["case_id"],
                    primary_alert_id=primary["alert_identifier"],
                    duplicate_case_id=dup["case_id"],
                    duplicate_alert_id=dup["alert_identifier"],
                    duplicate_rule_generator=dup["rule_generator"],
                    uid=uid,
                    case_type=case_type,
                    close_root_cause=close_root_cause,
                    close_reason=close_reason,
                    dry_run=dry_run,
                )
                if did_close:
                    closed_duplicates_count += 1
            except Exception as e:
                failed_duplicates_count += 1
                siemplify.LOGGER.error(
                    "Failed to close duplicate case {} (primary {}): {}".format(dup["case_id"], primary["case_id"], e)
                )

    siemplify.LOGGER.info(
        "=== Done. Mode: {} | Merged: {} | Closed: {} | Failed: {} | "
        "Single-UID cases (skipped): {} | Self-pair guarded: {} | "
        "Dry Run: {} | Carry Over: {} ===".format(
            merge_mode,
            merged_duplicates_count,
            closed_duplicates_count,
            failed_duplicates_count,
            skipped_count,
            self_pair_skipped,
            dry_run,
            carry_over,
        )
    )
    siemplify.end_script()


def _strip_trailing_api(url):
    """Strip a trailing /api (legacy SOAR REST base) so v1beta paths compose cleanly."""
    url = (url or "").rstrip("/")
    if url.endswith("/api"):
        return url[:-4]
    return url


def _safe_get_one_platform_format(siemplify):
    """Return siemplify.sdk_config.one_platform_api_root_uri_format or None on older SDKs."""
    try:
        return siemplify.sdk_config.one_platform_api_root_uri_format
    except AttributeError:
        return None


def _auto_detect_instance_url(siemplify):
    """Build the v1beta cases:merge URL from siemplify.sdk_config.

    Returns (absolute_url, None) on success, or (None, reason) when sdk_config
    isn't populated (common on workers missing the one-platform env vars —
    caller should fall back to the Chronicle Instance Path override).
    """
    fmt = _safe_get_one_platform_format(siemplify)
    if not fmt:
        return None, "siemplify.sdk_config.one_platform_api_root_uri_format not available on this SDK version"
    try:
        base = fmt.format("v1beta")
    except Exception as e:
        return None, "could not render sdk_config format template: {}".format(e)
    if not _INSTANCE_PATH_RE.search(base):
        return None, "sdk_config template did not contain a projects/locations/instances path: {!r}".format(base)
    for token in _SDK_CONFIG_FALLBACK_TOKENS:
        if token in base:
            return None, (
                "sdk_config is using placeholder literals for the Chronicle "
                "resource path (token {!r} in {!r}); the SOAR runtime "
                "did not set the one-platform env vars on this worker".format(token, base)
            )
    return base.rstrip("/") + "/cases:merge", None


def _resolve_merge_url(siemplify, instance_path_override):
    """Return (absolute_url, source_label) for POSTing cases.merge, or
    (None, reason) if a URL can't be assembled.

    Resolution order (first match wins):
      1. Auto-detect via siemplify.sdk_config.one_platform_api_root_uri_format.
      2. Chronicle Instance Path override + siemplify.API_ROOT host (fallback).
    """
    url, _err = _auto_detect_instance_url(siemplify)
    if url:
        return url, "sdk_config.one_platform_api_root_uri_format (auto-detected)"

    path_override = (instance_path_override or "").strip().strip("/")
    if path_override and _INSTANCE_PATH_RE.search("/" + path_override):
        api_root = (getattr(siemplify, "API_ROOT", None) or "").rstrip("/")
        host = _strip_trailing_api(api_root)
        if not host:
            return (
                None,
                "Chronicle Instance Path given but siemplify.API_ROOT is empty; cannot derive host",
            )
        return (
            "{}/v1beta/{}/cases:merge".format(host, path_override),
            "Chronicle Instance Path override + auto-derived host",
        )

    return (
        None,
        "auto-detection failed and no valid Chronicle Instance Path override provided",
    )


def _merge_cases_v1beta(
    siemplify,
    merge_url,
    primary_case_id,
    duplicate_case_id,
    duplicate_rule_generator,
    uid,
    case_type,
    dry_run,
):
    """POST the documented v1beta cases.merge endpoint to fold a duplicate DRP
    case into the primary.

      Body:     {"casesIds": [dup, primary], "caseToMergeWith": primary}
      Response: {"newCaseId": int, "isRequestValid": bool, "errors": [str]}
      IAM:      chronicle.cases.update
      Docs:     https://docs.cloud.google.com/chronicle/docs/reference/rest/v1beta/projects.locations.instances.cases/merge

    Re-verifies rule_generator right before POSTing in case the case got
    re-classified between discovery and merge.
    """
    rg = (duplicate_rule_generator or "").strip()
    if not (rg == case_type or rg.startswith(case_type + ":")):
        siemplify.LOGGER.warn(
            "Skipping merge of case {}: rule_generator {!r} no longer matches '{}' prefix.".format(
                duplicate_case_id, rg, case_type
            )
        )
        return False

    try:
        dup_id_int = int(duplicate_case_id)
        primary_id_int = int(primary_case_id)
    except (TypeError, ValueError):
        siemplify.LOGGER.warn(
            "Skipping merge: case IDs must be integers (got duplicate={!r}, "
            "primary={!r}). cases.merge rejects non-integer IDs.".format(duplicate_case_id, primary_case_id)
        )
        return False

    # IMPORTANT: casesIds is the full selection and MUST include
    # caseToMergeWith. Passing only the duplicate here makes the server
    # return "Cannot merge cases with case that is not selected!"
    body = {
        "casesIds": [dup_id_int, primary_id_int],
        "caseToMergeWith": primary_id_int,
    }

    if dry_run:
        siemplify.LOGGER.info(
            "[DRY RUN] Would POST {} with body {} (merge duplicate case {} into primary {} for UID {}…).".format(
                merge_url, body, duplicate_case_id, primary_case_id, uid[:16]
            )
        )
        return True

    siemplify.LOGGER.info(
        "[MERGE] POST {} body={} (duplicate={}, primary={}, uid={}…)".format(
            merge_url, body, duplicate_case_id, primary_case_id, uid[:16]
        )
    )
    resp = siemplify.session.post(merge_url, json=body)
    try:
        resp.raise_for_status()
    except Exception as e:
        body_text = ""
        try:
            body_text = resp.text
        except Exception:
            pass
        siemplify.LOGGER.error(
            "cases.merge call failed for duplicate {} → primary {}: {} | body={}".format(
                duplicate_case_id, primary_case_id, e, body_text
            )
        )
        raise

    try:
        result = resp.json() or {}
    except ValueError:
        result = {}

    is_valid = bool(result.get("isRequestValid", True))
    errors = result.get("errors") or []
    new_case_id = result.get("newCaseId")

    if not is_valid or errors:
        siemplify.LOGGER.error(
            "cases.merge returned an invalid/failed response for duplicate {} → "
            "primary {}: isRequestValid={}, errors={}, newCaseId={}".format(
                duplicate_case_id, primary_case_id, is_valid, errors, new_case_id
            )
        )
        return False

    siemplify.LOGGER.info(
        "Merged duplicate case {} into primary {} for UID {}…. newCaseId={}.".format(
            duplicate_case_id, primary_case_id, uid[:16], new_case_id
        )
    )
    return True


def _close_duplicate_with_reference(
    siemplify,
    primary_case_id,
    primary_alert_id,
    duplicate_case_id,
    duplicate_alert_id,
    duplicate_rule_generator,
    uid,
    case_type,
    close_root_cause,
    close_reason,
    dry_run,
):
    """Close a duplicate DRP case and leave a back-reference comment on the primary.

    Re-verifies rule_generator right before closing to guard against a race
    where the case gets re-classified between discovery and close.
    """
    rg = (duplicate_rule_generator or "").strip()
    if not (rg == case_type or rg.startswith(case_type + ":")):
        siemplify.LOGGER.warn(
            "Skipping close of case {}: rule_generator {!r} no longer matches '{}' prefix.".format(
                duplicate_case_id, rg, case_type
            )
        )
        return False

    if dry_run:
        siemplify.LOGGER.info(
            "[DRY RUN] Would close duplicate case {} (alert {}) and comment back on primary {} for UID {}….".format(
                duplicate_case_id, duplicate_alert_id, primary_case_id, uid[:16]
            )
        )
        return True

    siemplify.close_case(
        root_cause=close_root_cause,
        comment=(
            "[DRP Dedup] Duplicate of case {} (violation UID {}). Auto-closed by Dedup Job.".format(
                primary_case_id, uid
            )
        ),
        reason=close_reason,
        case_id=duplicate_case_id,
        alert_identifier=duplicate_alert_id,
    )
    siemplify.add_comment(
        "[DRP Dedup] Closed duplicate case {} (same violation UID {}).".format(duplicate_case_id, uid),
        primary_case_id,
        primary_alert_id,
    )
    siemplify.LOGGER.info(
        "Closed duplicate case {} referencing primary {} for UID {}….".format(
            duplicate_case_id, primary_case_id, uid[:16]
        )
    )
    return True


def _carry_over_to_primary(siemplify, primary, duplicate, dry_run):
    """Copy analyst-authored artifacts (comments, tags, entities) from the
    duplicate to the primary before the duplicate is closed.

    Each sub-step is independently try/except'd so a failure in one doesn't
    block the others or the subsequent close_case call. Skips '[DRP Dedup]'
    comments (our own back-references) and entities already on the primary.
    """
    primary_case_id = primary["case_id"]
    primary_alert_id = primary["alert_identifier"]
    duplicate_case_id = duplicate["case_id"]

    # ── 1. Comments ─────────────────────────────────────────────────────────
    try:
        comments = siemplify.get_case_comments(duplicate_case_id) or []
    except Exception as e:
        siemplify.LOGGER.warn("Could not fetch comments from duplicate {}: {}".format(duplicate_case_id, e))
        comments = []

    for c in comments:
        text = (c.get("comment") or c.get("comment_text") or c.get("text") or "").strip()
        if not text:
            continue
        if text.startswith("[DRP Dedup]"):
            continue
        wrapped = "[from merged case #{}] {}".format(duplicate_case_id, text)
        if dry_run:
            siemplify.LOGGER.info(
                "[DRY RUN] Would carry over comment to primary {}: {!r}".format(primary_case_id, text[:80])
            )
            continue
        try:
            siemplify.add_comment(wrapped, primary_case_id, primary_alert_id)
        except Exception as e:
            siemplify.LOGGER.warn(
                "add_comment failed while carrying over from case {} to primary {}: {}".format(
                    duplicate_case_id, primary_case_id, e
                )
            )

    # ── 2. Tags (case-level + alert-level on the duplicate) ─────────────────
    primary_case_tags = {_tag_name(t) for t in (primary.get("case_tags") or []) if _tag_name(t)}
    primary_alert_tags = {_tag_name(t) for t in (primary.get("alert_tags") or []) if _tag_name(t)}
    already_present = primary_case_tags | primary_alert_tags

    incoming_tags = list(duplicate.get("case_tags") or []) + list(duplicate.get("alert_tags") or [])
    for raw_tag in incoming_tags:
        tag = _tag_name(raw_tag)
        if not tag or tag in already_present:
            continue
        if dry_run:
            siemplify.LOGGER.info("[DRY RUN] Would add tag {!r} to primary {}".format(tag, primary_case_id))
            already_present.add(tag)
            continue
        try:
            siemplify.add_tag(tag, primary_case_id, primary_alert_id)
            already_present.add(tag)
        except Exception as e:
            siemplify.LOGGER.warn(
                "add_tag {!r} failed on primary {} (from duplicate {}): {}".format(
                    tag, primary_case_id, duplicate_case_id, e
                )
            )

    # ── 3. Entities (from the duplicate's DRP alert) ────────────────────────
    primary_entity_ids = {
        (e.get("identifier") or "").strip() for e in (primary.get("entities") or []) if e.get("identifier")
    }

    environment = primary.get("environment") or duplicate.get("environment")

    for ent in duplicate.get("entities") or []:
        ident = (ent.get("identifier") or "").strip()
        if not ident or ident in primary_entity_ids:
            continue

        ent_type = ent.get("entity_type") or ent.get("type") or "DestinationURL"
        properties = ent.get("additional_properties") or ent.get("properties") or {}
        is_suspicious = bool(ent.get("is_suspicious", False))

        if dry_run:
            siemplify.LOGGER.info(
                "[DRY RUN] Would add entity {!r} (type={}) to primary {}".format(ident, ent_type, primary_case_id)
            )
            primary_entity_ids.add(ident)
            continue

        try:
            siemplify.add_entity_to_case(
                case_id=primary_case_id,
                alert_identifier=primary_alert_id,
                entity_identifier=ident,
                entity_type=ent_type,
                is_internal=bool(ent.get("is_internal", False)),
                is_suspicous=is_suspicious,
                is_enriched=bool(ent.get("is_enriched", False)),
                is_vulnerable=bool(ent.get("is_vulnerable", False)),
                properties=properties,
                environment=environment,
            )
            primary_entity_ids.add(ident)
        except Exception as e:
            siemplify.LOGGER.warn(
                "add_entity_to_case failed for {!r} on primary {} (from duplicate {}): {}".format(
                    ident, primary_case_id, duplicate_case_id, e
                )
            )


def _tag_name(tag):
    """Normalize a tag to a string. Tenants return tags as bare strings or as
    dicts with a 'name'/'tag' field; accept both."""
    if isinstance(tag, str):
        return tag.strip()
    if isinstance(tag, dict):
        return (tag.get("name") or tag.get("tag") or "").strip()
    return ""


if __name__ == "__main__":
    main()
