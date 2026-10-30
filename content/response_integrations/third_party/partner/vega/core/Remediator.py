"""Map closed SecOps Vega cases back to Vega status-only mutations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

from .constants import (
    ENTITY_TYPE_ALERT,
    ENTITY_TYPE_INCIDENT,
    NESTED_RELATED_KEY,
    SOAR_ALERT_TYPE_INCIDENT,
    SOAR_CASE_DETAILS_PATH,
    SOAR_CASE_SEARCH_PATH,
    SOAR_CASE_STATUS_CLOSED,
    SOAR_CASE_STATUS_OPEN,
    SOAR_DETAILS_GET_CAP,
    SOAR_SEARCH_PAGE_SIZE,
    SOAR_TIME_RANGE_MODIFIED,
    VENDOR_NAME,
)
from .sync_targets import SYNC_MODE_INCIDENT, extract_sync_targets
from .utils import parse_iso_timestamp, safe_log, utc_now

_SOAR_TIMEOUT = 30
_TRACKED_CAP = 5000


def ingest_skip_ids(records: list[tuple[str, SingleJson]] | None) -> set[str]:
    """Vega IDs packaged this poll must not be resolved on the same run."""
    from .mapping import record_alert_ids, record_id

    skip: set[str] = set()
    for entity_type, record in records or []:
        if not isinstance(record, dict):
            continue
        identifier = record_id(record, entity_type)
        if identifier:
            skip.add(identifier)
        if entity_type == ENTITY_TYPE_ALERT:
            skip.update(record_alert_ids(record))
        for related in record.get(NESTED_RELATED_KEY) or []:
            if isinstance(related, dict):
                skip.update(record_alert_ids(related))
    return {item for item in skip if item}


def ingest_sync_refs(records: list[tuple[str, SingleJson]] | None) -> list[SingleJson]:
    """Case lookup keys: SOAR ticket, human Vega IDs, and case title."""
    from .mapping import case_display_name, record_display_id, record_id, soar_meta

    refs: list[SingleJson] = []
    seen: set[str] = set()
    for entity_type, record in records or []:
        if not isinstance(record, dict):
            continue
        identifier = record_id(record, entity_type)
        if not identifier:
            continue
        meta = soar_meta(record)
        suffix = str(meta.get("ticket_suffix") or "").strip()
        ticket_key = f"{identifier}:{suffix}" if suffix else identifier
        ticket = f"{VENDOR_NAME}:{ticket_key}"
        if ticket in seen:
            continue
        seen.add(ticket)
        display = record_display_id(record, entity_type)
        title = str(meta.get("case_title") or case_display_name(record, entity_type) or "").strip()
        tokens = []
        for item in (ticket, ticket_key, identifier, display):
            text = str(item or "").strip()
            if text and text not in tokens:
                tokens.append(text)
        refs.append({"ticket": ticket, "tokens": tokens, "title": title})
    return refs


def ingest_ticket_ids(records: list[tuple[str, SingleJson]] | None) -> list[str]:
    """SOAR ticket IDs the packager assigns: ``Vega:<record_id>``."""
    return [str(item.get("ticket") or "") for item in ingest_sync_refs(records) if item.get("ticket")]


_CLOSED_STATUS_NAMES = {"closed", "close"}
_OPEN_STATUS_NAMES = {"open", "opened", "new", "inprogress", "in progress"}
_SOAR_CLOSED_FLAG_KEYS = (
    "isClosed",
    "isCaseClosed",
    "IsCaseClosed",
    "caseClosed",
)
_SOAR_STATUS_NAME_KEYS = ("statusName", "caseStatusName")


def _ci_get(payload: SingleJson, *keys: str) -> Any:
    if not isinstance(payload, dict):
        return None
    lowered = {str(key).lower(): value for key, value in payload.items()}
    for key in keys:
        if key.lower() in lowered and lowered[key.lower()] not in (None, ""):
            return lowered[key.lower()]
    return None


def _first_present(payload: SingleJson, keys: tuple[str, ...]) -> Any:
    return _ci_get(payload, *keys)


def _is_vega_event_payload(payload: SingleJson) -> bool:
    return bool(
        payload.get("vega_id")
        or payload.get("vegaId")
        or payload.get("vega_entity_type")
        or payload.get("vegaEntityType")
    )


def _explicit_soar_closed_flag(payload: SingleJson) -> bool | None:
    """SOAR closed flag only. None means the payload has no case-closed field.

    Vega events map ``status`` / ``userStatus`` (OPEN/RESOLVED) onto the same
    case dict. Those fields are not a SecOps close and must not trigger
    outbound resolve.
    """
    flag = _first_present(payload, _SOAR_CLOSED_FLAG_KEYS)
    if isinstance(flag, bool):
        return flag
    if isinstance(flag, (int, float)) and not isinstance(flag, bool):
        return int(flag) != 0
    if flag is not None:
        text = str(flag).strip().lower()
        if text in ("true", "yes"):
            return True
        if text in ("false", "no"):
            return False
    name = _first_present(payload, _SOAR_STATUS_NAME_KEYS)
    if name is not None:
        text = str(name).strip().lower().replace("_", " ")
        if text in _CLOSED_STATUS_NAMES:
            return True
        if text in _OPEN_STATUS_NAMES:
            return False
    return None


def _soar_numeric_status_closed(payload: SingleJson) -> bool | None:
    """CaseDataStatus on a SOAR case dict. None for Vega event payloads."""
    if _is_vega_event_payload(payload):
        return None
    value = _ci_get(payload, "status", "Status")
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.isdigit():
            value = int(text)
        else:
            lowered = text.lower().replace("_", " ")
            if lowered in _CLOSED_STATUS_NAMES:
                return True
            if lowered in _OPEN_STATUS_NAMES:
                return False
            return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = int(value)
    if number == SOAR_CASE_STATUS_CLOSED:
        return True
    if number in SOAR_CASE_STATUS_OPEN:
        return False
    return None


def is_soar_case_closed(payload: SingleJson) -> bool:
    """True only when SecOps/SOAR marks the case closed.

    Accepts ``isClosed`` / ``statusName=CLOSED`` / numeric ``status=2``
    (CaseDataStatus.CLOSED). Vega event ``status`` / ``userStatus``
    (OPEN/RESOLVED) is ignored.
    """
    if not isinstance(payload, dict):
        return False
    nested = (
        payload.get("case")
        or payload.get("Case")
        or payload.get("caseInfo")
        or payload.get("case_info")
        or payload.get("caseDetails")
        or payload.get("CaseDetails")
    )
    if isinstance(nested, dict) and not _is_vega_event_payload(nested):
        nested_flag = is_soar_case_closed(nested)
        explicit = _explicit_soar_closed_flag(payload)
        if explicit is False:
            return False
        numeric = _soar_numeric_status_closed(payload)
        if numeric is False:
            return False
        if nested_flag:
            return True
    flag = _explicit_soar_closed_flag(payload)
    if flag is not None:
        return flag
    numeric = _soar_numeric_status_closed(payload)
    return bool(numeric)


def _ticket_body(ticket: str) -> str:
    text = str(ticket or "").strip()
    prefix = f"{VENDOR_NAME}:"
    if text.startswith(prefix):
        return text[len(prefix) :]
    return text


def _case_id(row: SingleJson) -> str:
    value = _ci_get(row, "id", "Id", "ID", "identifier", "Identifier", "caseId", "CaseId")
    return str(value).strip() if value not in (None, "") else ""


def _case_title(row: SingleJson) -> str:
    value = _ci_get(row, "title", "Title", "name", "Name", "displayName", "DisplayName")
    return str(value).strip() if value not in (None, "") else ""


def _is_incident_case_title(payload: SingleJson) -> bool:
    """True for the Vega incident case, not the related-alerts case.

    ``(related alerts)`` is the current title. ``(cluster N)`` (and legacy
    ``(batch N)``) mark related-alert chunks so they resolve alerts instead of
    the incident.
    """
    from .mapping import RELATED_ALERTS_TITLE_MARK

    title = _case_title(payload)
    if not title:
        return False
    lowered = title.lower()
    if RELATED_ALERTS_TITLE_MARK in lowered or "(cluster " in lowered or "(batch " in lowered:
        return False
    return lowered.startswith(SOAR_ALERT_TYPE_INCIDENT.lower())


def _unwrap_case(payload: Any) -> SingleJson:
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        payload = payload[0]
    if not isinstance(payload, dict):
        return {}
    for key in ("case", "Case", "caseDetails", "CaseDetails", "caseInfo", "case_info", "data"):
        nested = payload.get(key)
        if not isinstance(nested, dict):
            continue
        if _case_id(nested) or nested.get("alerts") or nested.get("alertCards") or nested.get("cyberAlerts"):
            merged = dict(payload)
            merged.update(nested)
            return merged
    return payload


def _row_text(row: SingleJson) -> str:
    parts = []
    for value in row.values() if isinstance(row, dict) else []:
        if isinstance(value, (str, int, float, bool)) and value not in (None, ""):
            parts.append(str(value).strip())
    return " ".join(parts)


def _usable_tokens(ref: SingleJson) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    ticket = str(ref.get("ticket") or "").strip()
    for item in (ticket, *(ref.get("tokens") or [])):
        text = str(item or "").strip()
        lowered = text.lower()
        if len(text) < 4 or lowered in seen:
            continue
        if text == VENDOR_NAME or text == f"{VENDOR_NAME}:":
            continue
        seen.add(lowered)
        tokens.append(text)
    return tokens


def _row_matches_ref(row: SingleJson, ref: SingleJson) -> bool:
    if not isinstance(row, dict) or not isinstance(ref, dict):
        return False
    blob = _row_text(row).lower()
    for token in _usable_tokens(ref):
        if token.lower() in blob:
            return True
    title = str(ref.get("title") or "").strip().lower()
    row_title = _case_title(row).lower()
    return bool(title and row_title and (title in row_title or row_title in title))


def _payload_identity_blob(payload: SingleJson) -> str:
    try:
        return json.dumps(payload, default=str).lower()
    except Exception:
        return _row_text(payload).lower()


def _payload_matches_ref(payload: SingleJson, ref: SingleJson) -> bool:
    if _row_matches_ref(payload, ref):
        return True
    blob = _payload_identity_blob(payload)
    return any(token.lower() in blob for token in _usable_tokens(ref))


def _explicitly_open(payload: SingleJson) -> bool:
    flag = _explicit_soar_closed_flag(payload)
    if flag is False:
        return True
    numeric = _soar_numeric_status_closed(payload)
    return numeric is False


def _search_row_closed(row: SingleJson) -> bool:
    flag = _explicit_soar_closed_flag(row)
    if flag is True:
        return True
    numeric = _soar_numeric_status_closed(row)
    return bool(numeric)


def _treat_as_closed(merged: SingleJson, row: SingleJson) -> bool:
    if _explicitly_open(merged):
        return False
    if is_soar_case_closed(merged):
        return True
    return _search_row_closed(row)


def _normalize_ref(item: Any) -> SingleJson:
    if isinstance(item, dict) and str(item.get("ticket") or "").startswith(f"{VENDOR_NAME}:"):
        tokens = [str(token).strip() for token in (item.get("tokens") or []) if str(token).strip()]
        ticket = str(item.get("ticket")).strip()
        body = _ticket_body(ticket)
        for extra in (ticket, body):
            if extra and extra not in tokens:
                tokens.append(extra)
        return {
            "ticket": ticket,
            "tokens": tokens,
            "title": str(item.get("title") or "").strip(),
        }
    ticket = str(item or "").strip()
    if not ticket.startswith(f"{VENDOR_NAME}:"):
        return {}
    body = _ticket_body(ticket)
    return {"ticket": ticket, "tokens": [ticket, body], "title": ""}


def _merge_tracked_refs(
    state: SingleJson, ingest_refs: list | None, ingest_tickets: list[str] | None
) -> list[SingleJson]:
    ordered: list[SingleJson] = []
    by_ticket: dict[str, SingleJson] = {}
    raw = list(state.get("tracked_refs") or []) + list(state.get("tracked_tickets") or [])
    raw.extend(ingest_refs or [])
    raw.extend(ingest_tickets or [])
    for item in raw:
        ref = _normalize_ref(item)
        ticket = ref.get("ticket") or ""
        if not ticket:
            continue
        existing = by_ticket.get(ticket)
        if existing is None:
            by_ticket[ticket] = ref
            ordered.append(ref)
            continue
        tokens = list(existing.get("tokens") or [])
        for token in ref.get("tokens") or []:
            if token not in tokens:
                tokens.append(token)
        existing["tokens"] = tokens
        if not existing.get("title") and ref.get("title"):
            existing["title"] = ref["title"]
    return ordered[-_TRACKED_CAP:]


def _prune_tracked_refs(refs: list[SingleJson], processed: set[str]) -> list[SingleJson]:
    kept: list[SingleJson] = []
    for ref in refs:
        ticket = str(ref.get("ticket") or "")
        body = _ticket_body(ticket)
        if ticket in processed or body in processed:
            continue
        drop = False
        for item in processed:
            token = str(item).strip()
            if not token or token.startswith("case:"):
                continue
            if ticket == f"{VENDOR_NAME}:{token}" or ticket.startswith(f"{VENDOR_NAME}:{token}:"):
                drop = True
                break
            if token in (ref.get("tokens") or []):
                drop = True
                break
        if not drop:
            kept.append(ref)
    return kept


def _api_root(siemplify: Any) -> str:
    return str(getattr(siemplify, "API_ROOT", "") or getattr(siemplify, "api_root", "") or "").rstrip("/")


def _environment(siemplify: Any) -> str:
    try:
        return str(siemplify.context.connector_info.environment or "").strip()
    except Exception:
        return ""


def _json_response(response: Any) -> SingleJson:
    if response is None:
        return {}
    raise_for_status = getattr(response, "raise_for_status", None)
    if callable(raise_for_status):
        raise_for_status()
    parser = getattr(response, "json", None)
    if not callable(parser):
        return {}
    payload = parser()
    if isinstance(payload, list):
        return {"results": payload}
    return payload if isinstance(payload, dict) else {}


def _iso_ms(millis: int) -> str:
    return datetime.fromtimestamp(max(0, int(millis)) / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _time_to_ms(value) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if number > 1e12:
            return int(number)
        if number > 1e9:
            return int(number * 1000)
        return 0
    parsed = parse_iso_timestamp(str(value))
    if parsed is None:
        return 0
    return int(parsed.timestamp() * 1000)


def _case_close_ms(payload: SingleJson) -> int:
    return _time_to_ms(
        _ci_get(
            payload,
            "closedTime",
            "closeTime",
            "closureTime",
            "updateTime",
            "lastUpdateTime",
            "updatedTime",
            "modificationTimeUnixTimeInMs",
            "modification_time_unix_time_in_ms",
        )
    )


def _closed_after_since(payload: SingleJson, since_ms: int, require_time: bool) -> bool:
    closed_ms = _case_close_ms(payload)
    if closed_ms:
        return closed_ms >= since_ms
    return not require_time


def _id_is_tracked(identifier: str, refs: list[SingleJson]) -> bool:
    needle = str(identifier or "").strip().lower()
    if not needle or not refs:
        return False
    for ref in refs:
        for token in _usable_tokens(ref):
            token_l = token.lower()
            if needle == token_l or needle == _ticket_body(token).lower():
                return True
    return False


def _row_matches_any_ref(row: SingleJson, refs: list[SingleJson]) -> bool:
    return any(_row_matches_ref(row, ref) for ref in refs)


def _payload_matches_any_ref(payload: SingleJson, refs: list[SingleJson]) -> bool:
    return any(_payload_matches_ref(payload, ref) for ref in refs)


def _tracked_target_ids(identifiers: list[str], refs: list[SingleJson]) -> list[str]:
    return [item for item in identifiers if _id_is_tracked(item, refs)]


class SoarRemediator:
    """Close matching Vega alerts or incidents when SOAR cases close."""

    def __init__(self, manager: Any, siemplify: Any, logger_instance: Any = None) -> None:
        self.manager = manager
        self.siemplify = siemplify
        self.logger = logger_instance

    def run_once(
        self,
        state: SingleJson,
        skip_ids: set[str] | None = None,
        ingest_tickets: list[str] | None = None,
        ingest_refs: list[SingleJson] | None = None,
    ) -> SingleJson:
        """Scan recently modified SOAR cases and resolve matching Vega entities.

        Tracks ingested tickets across polls and skips ids packaged in this run.
        """
        state = dict(state or {})
        processed = set(state.get("processed_ids") or [])
        current_skip = {str(item).strip() for item in (skip_ids or []) if str(item).strip()}
        now_ms = int(utc_now().timestamp() * 1000)
        extra_tickets = list(ingest_tickets or [])
        if not extra_tickets and not ingest_refs and current_skip:
            extra_tickets = [f"{VENDOR_NAME}:{item}" for item in current_skip]
        refs = _merge_tracked_refs(state, ingest_refs, extra_tickets)
        tickets = [str(item.get("ticket") or "") for item in refs if item.get("ticket")]
        last_check_ms = int(state.get("last_check_ms") or 0)
        if last_check_ms <= 0:
            state["processed_ids"] = list(processed)[-_TRACKED_CAP:]
            state["last_check_ms"] = now_ms
            state["recent_ingest_ids"] = list(current_skip)[-_TRACKED_CAP:]
            state["tracked_tickets"] = tickets
            state["tracked_refs"] = refs
            safe_log(
                self.logger,
                "info",
                "Outbound Vega sync baseline set; cases closed after this run will sync.",
            )
            return {
                "state": state,
                "message": "Close-sync baseline set (no historical closes sent).",
            }

        skip = current_skip
        cases, remember_ids = self._closed_vega_cases(last_check_ms, now_ms, refs, processed)
        for case_id in remember_ids:
            processed.add(f"case:{case_id}")
        synced = 0
        synced_ids: set[str] = set()
        for case_payload in cases:
            case_key = _case_id(case_payload)
            processed_key = f"case:{case_key}" if case_key else ""
            if processed_key and processed_key in processed:
                continue
            if not is_soar_case_closed(case_payload):
                continue
            targets = extract_sync_targets(case_payload)
            mode = targets.get("mode")
            raw_incident_ids = list(targets.get("incident_ids") or [])
            raw_alert_ids = list(targets.get("alert_ids") or [])
            incident_ids = _tracked_target_ids(
                [item for item in raw_incident_ids if item not in processed and item not in skip],
                refs,
            )
            alert_ids = _tracked_target_ids(
                [item for item in raw_alert_ids if item not in processed and item not in skip],
                refs,
            )
            skipped_ingest = any(item in skip for item in raw_incident_ids) or any(
                item in skip for item in raw_alert_ids
            )
            if not incident_ids and not alert_ids:
                if (
                    processed_key
                    and not skipped_ingest
                    and (_tracked_target_ids(raw_incident_ids + raw_alert_ids, refs))
                ):
                    processed.add(processed_key)
                continue
            if mode == SYNC_MODE_INCIDENT and not incident_ids:
                continue
            if mode != SYNC_MODE_INCIDENT and not alert_ids:
                continue
            try:
                if mode == SYNC_MODE_INCIDENT:
                    self.manager.resolve_incidents(incident_ids)
                    processed.update(incident_ids)
                    synced_ids.update(incident_ids)
                    synced += 1
                elif alert_ids:
                    self.manager.resolve_alerts(alert_ids)
                    processed.update(alert_ids)
                    synced_ids.update(alert_ids)
                    synced += 1
                if processed_key:
                    processed.add(processed_key)
            except Exception as exc:
                entity_type = ENTITY_TYPE_INCIDENT if mode == SYNC_MODE_INCIDENT else ENTITY_TYPE_ALERT
                safe_log(
                    self.logger,
                    "warn",
                    "Failed to sync Vega %s %s: %s",
                    entity_type,
                    case_key or incident_ids or alert_ids,
                    exc,
                )
        processed.update(synced_ids)
        state["processed_ids"] = list(processed)[-_TRACKED_CAP:]
        state["last_check_ms"] = now_ms
        state["recent_ingest_ids"] = list(current_skip)[-_TRACKED_CAP:]
        pruned = _prune_tracked_refs(refs, processed)
        state["tracked_refs"] = pruned
        state["tracked_tickets"] = [str(item.get("ticket") or "") for item in pruned if item.get("ticket")]
        return {
            "state": state,
            "message": f"Synced {synced} closed Vega case(s).",
        }

    def _closed_vega_cases(
        self,
        since_ms: int,
        until_ms: int,
        refs: list[SingleJson],
        processed: set[str],
    ) -> tuple[list[SingleJson], list[str]]:
        session = getattr(self.siemplify, "session", None)
        root = _api_root(self.siemplify)
        if session is not None and root:
            if not refs:
                safe_log(
                    self.logger,
                    "info",
                    "Close-sync has no ingested Vega tickets to check.",
                )
                return [], []
            return self._closed_cases_from_rest(since_ms, until_ms, refs, processed)
        return self._closed_cases_from_sdk(since_ms, refs), []

    def _closed_cases_from_sdk(self, since_ms: int, refs: list[SingleJson]) -> list[SingleJson]:
        method = getattr(
            self.siemplify,
            "get_alerts_ticket_ids_from_cases_closed_since_timestamp",
            None,
        )
        getter = getattr(self.siemplify, "get_cases_by_ticket_id", None)
        if not callable(method) or not callable(getter):
            safe_log(
                self.logger,
                "warn",
                "Outbound Vega sync skipped: connector has no SOAR session/API_ROOT to search closed cases.",
            )
            return []
        try:
            ticket_ids = method(int(since_ms)) or []
        except TypeError:
            return []
        except Exception as exc:
            safe_log(self.logger, "warn", "Closed-case SDK lookup failed: %s", exc)
            return []
        cases: list[SingleJson] = []
        for ticket_id in ticket_ids:
            if not str(ticket_id).startswith(f"{VENDOR_NAME}:"):
                continue
            try:
                payload = getter(ticket_id) or {}
            except Exception as exc:
                safe_log(self.logger, "warn", "Case fetch failed for %s: %s", ticket_id, exc)
                continue
            if not isinstance(payload, dict) or not payload:
                continue
            if refs and not _payload_matches_any_ref(payload, refs):
                targets = extract_sync_targets(payload)
                ids = list(targets.get("incident_ids") or []) + list(targets.get("alert_ids") or [])
                if not _tracked_target_ids(ids, refs):
                    continue
            cases.append(payload)
        return cases

    def _closed_cases_from_rest(
        self,
        since_ms: int,
        until_ms: int,
        refs: list[SingleJson],
        processed: set[str],
    ) -> tuple[list[SingleJson], list[str]]:
        session = getattr(self.siemplify, "session", None)
        root = _api_root(self.siemplify)
        summaries = self._search_closed_case_summaries(session, root, since_ms, until_ms)
        dump = len(summaries) >= SOAR_SEARCH_PAGE_SIZE
        if dump:
            safe_log(
                self.logger,
                "info",
                "Close-sync SOAR search returned %s rows (time filter ignored); "
                "fetching matching ingested cases and syncing only if details "
                "closed after the last poll.",
                len(summaries),
            )
        cases: list[SingleJson] = []
        remember_ids: list[str] = []
        fetched = 0
        seen_ids: set[str] = set()
        for summary in summaries:
            title = _case_title(summary)
            if title and not title.startswith(VENDOR_NAME):
                continue
            case_id = _case_id(summary)
            if not case_id or case_id in seen_ids:
                continue
            if f"case:{case_id}" in processed:
                continue
            if dump:
                summary_ms = _case_close_ms(summary)
                if summary_ms and summary_ms < since_ms:
                    continue
                if refs and not _row_matches_any_ref(summary, refs):
                    continue
            elif not _closed_after_since(summary, since_ms, require_time=False):
                continue
            if fetched >= SOAR_DETAILS_GET_CAP:
                break
            details = self._get_case_details(session, root, case_id)
            fetched += 1
            seen_ids.add(case_id)
            merged = dict(summary)
            if details:
                merged.update(details)
            if _explicitly_open(merged):
                continue
            if not is_soar_case_closed(merged) and not _search_row_closed(summary):
                continue
            if dump and not _closed_after_since(merged, since_ms, require_time=True):
                if details:
                    remember_ids.append(case_id)
                continue
            if refs and not _payload_matches_any_ref(merged, refs):
                targets = extract_sync_targets(merged)
                ids = list(targets.get("incident_ids") or []) + list(targets.get("alert_ids") or [])
                if not _tracked_target_ids(ids, refs):
                    continue
            cases.append(merged)
        safe_log(
            self.logger,
            "info",
            "Close-sync found %s closed Vega case(s) via SOAR search (%s row(s), dump=%s).",
            len(cases),
            len(summaries),
            dump,
        )
        return cases, remember_ids

    def _search_closed_case_summaries(self, session, root: str, since_ms: int, until_ms: int) -> list[SingleJson]:
        url = f"{root}/{SOAR_CASE_SEARCH_PATH}?format=camel"
        environment = _environment(self.siemplify)
        payload = {
            "isCaseClosed": True,
            "title": VENDOR_NAME,
            "startTime": _iso_ms(since_ms),
            "endTime": _iso_ms(until_ms),
            "timeRangeFilter": SOAR_TIME_RANGE_MODIFIED,
            "pageSize": SOAR_SEARCH_PAGE_SIZE,
            "requestedPage": 0,
        }
        if environment:
            payload["environments"] = [environment]
        try:
            response = session.post(url, json=payload, timeout=_SOAR_TIMEOUT)
            body = _json_response(response)
        except Exception as exc:
            safe_log(self.logger, "warn", "Closed-case SOAR search failed: %s", exc)
            return []
        rows = body.get("results") or body.get("Results") or []
        if not isinstance(rows, list):
            return []
        return [row for row in rows if isinstance(row, dict)]

    def _get_case_details(self, session, root: str, case_id: str) -> SingleJson:
        path = SOAR_CASE_DETAILS_PATH.format(case_id=case_id)
        url = f"{root}/{path}?format=camel"
        try:
            response = session.get(url, timeout=_SOAR_TIMEOUT)
            payload = _unwrap_case(_json_response(response))
        except Exception as exc:
            safe_log(
                self.logger,
                "warn",
                "GetCaseFullDetails failed for case %s: %s",
                case_id,
                exc,
            )
            return {}
        return payload if isinstance(payload, dict) else {}
