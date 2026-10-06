"""
Auto-remediation sync: closed SOAR Flare cases → Flare remediate.

Uses SOAR SDK only (no Google service account):
  - First run: fetch all closed Flare cases
  - Later runs: fetch closed since last_successful_check_timestamp
  - After a successful run: persist current UTC timestamp for the next lookup
  - Flare remediate API uses a fixed batch size of 10
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .constants import DEFAULT_FLARE_ACTION_BATCH_SIZE, VENDOR_NAME
from .utils import parse_iso_timestamp, safe_log, utc_now, utc_now_iso

logger = logging.getLogger(__name__)

# Epoch used when no remediation checkpoint exists yet ("get all closed cases").
_EPOCH_MS = 0

_UID_KEY_HINTS = {
    "product_log_id",
    "productlogid",
    "flare_uid",
    "flareuid",
    "flare_uids",
    "flareuids",
}


def _looks_like_flare_uid(value: str) -> bool:
    if not value or len(value) < 3:
        return False
    return value.count("/") >= 1 and " " not in value


def _add_uid_string(value: str, found: set) -> None:
    text = value.strip()
    if not text:
        return
    if "," in text:
        for part in text.split(","):
            part = part.strip()
            if _looks_like_flare_uid(part):
                found.add(part)
    elif _looks_like_flare_uid(text):
        found.add(text)


def extract_flare_uids_from_obj(obj: Any, found: Optional[set] = None) -> set:
    """Recursively collect Flare UIDs from a SOAR case/alert/event payload."""
    if found is None:
        found = set()

    if isinstance(obj, dict):
        key_name = obj.get("key")
        if isinstance(key_name, str) and key_name.lower() in _UID_KEY_HINTS:
            val = obj.get("value")
            if isinstance(val, str):
                _add_uid_string(val, found)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, str):
                        _add_uid_string(item, found)

        for key, value in obj.items():
            key_l = str(key).lower()
            if key_l in _UID_KEY_HINTS:
                if isinstance(value, str):
                    _add_uid_string(value, found)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            _add_uid_string(item, found)
            extract_flare_uids_from_obj(value, found)
    elif isinstance(obj, list):
        for item in obj:
            extract_flare_uids_from_obj(item, found)
    elif isinstance(obj, str):
        _add_uid_string(obj, found)
    else:
        try:
            attrs = getattr(obj, "__dict__", None)
            if isinstance(attrs, dict) and attrs:
                extract_flare_uids_from_obj(attrs, found)
        except Exception:
            pass

    return found


def _to_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    return [value]


def _case_is_flare(case_obj: Any) -> bool:
    """Heuristic: Flare connector cases are tagged / vendored with VENDOR_NAME."""
    try:
        if VENDOR_NAME in str(case_obj):
            return True
    except Exception:
        pass
    tags = []
    for attr in ("tags", "case_tags", "Tags"):
        raw = getattr(case_obj, attr, None)
        if raw:
            tags.extend([str(t) for t in _to_list(raw)])
    if isinstance(case_obj, dict):
        for key in ("tags", "case_tags", "Tags"):
            if case_obj.get(key):
                tags.extend([str(t) for t in _to_list(case_obj.get(key))])
    return VENDOR_NAME in tags or any(VENDOR_NAME in t for t in tags)


class SoarRemediator:
    """Sync closed SOAR Flare cases → Flare remediate (no Google SA)."""

    def __init__(
        self,
        flare_manager,
        siemplify,
        rule_generator: str = VENDOR_NAME,
        state: Optional[dict] = None,
        logger_instance=None,
    ) -> None:
        self.flare = flare_manager
        self.siemplify = siemplify
        self.action_batch_size = DEFAULT_FLARE_ACTION_BATCH_SIZE
        self.rule_generator = (rule_generator or VENDOR_NAME).strip() or VENDOR_NAME
        self.state = state if isinstance(state, dict) else {
            "last_successful_check_timestamp": None,
            "processed_alerts": {},
        }
        self.state.setdefault("processed_alerts", {})
        self.logger = logger_instance or logger

    def _log(self, level: str, msg: str, *args) -> None:
        safe_log(self.logger, level, msg, *args)

    def get_query_start_time(self) -> Optional[datetime]:
        """
        Return the last successful remediation timestamp, or None to mean
        "fetch all closed cases" on the first run.
        """
        return parse_iso_timestamp(self.state.get("last_successful_check_timestamp"))

    def _query_start_ms(self, start_time: Optional[datetime]) -> int:
        if start_time is None:
            return _EPOCH_MS
        return int(start_time.timestamp() * 1000)

    def _load_case(self, case_id: Any) -> Any:
        if case_id is None or case_id == "":
            return None
        for method_name in ("get_case_by_id", "_get_case_by_id"):
            method = getattr(self.siemplify, method_name, None)
            if not callable(method):
                continue
            try:
                return method(case_id)
            except Exception as exc:
                self._log("warning", "%s(%s) failed: %s", method_name, case_id, exc)
        return None

    def _cases_from_ticket_id(self, ticket_id: str) -> list:
        method = getattr(self.siemplify, "get_cases_by_ticket_id", None)
        if not callable(method):
            return []
        try:
            case_ids = _to_list(method(ticket_id))
        except Exception as exc:
            self._log("warning", "get_cases_by_ticket_id(%s) failed: %s", ticket_id, exc)
            return []
        cases = []
        for case_id in case_ids:
            case_obj = self._load_case(case_id)
            if case_obj is not None:
                cases.append((str(case_id), case_obj))
        return cases

    def _closed_case_ids(self, start_time: Optional[datetime]) -> list:
        method = getattr(self.siemplify, "get_cases_ids_by_filter", None)
        if not callable(method):
            return []
        kwargs = {
            "sort_by": "CLOSE_TIME",
            "sort_order": "DESC",
        }
        if start_time is not None:
            kwargs["close_time_from_unix_time_in_ms"] = self._query_start_ms(start_time)
        try:
            return _to_list(method("CLOSE", **kwargs))
        except TypeError:
            try:
                return _to_list(method("CLOSE"))
            except Exception as exc:
                self._log("warning", "get_cases_ids_by_filter failed: %s", exc)
                return []
        except Exception as exc:
            self._log("warning", "get_cases_ids_by_filter failed: %s", exc)
            return []

    def fetch_closed_flare_cases(self, start_time: Optional[datetime]) -> list:
        """Return list of (case_key, case_payload) for closed Flare cases."""
        results: list = []
        seen_keys: set = set()
        ts_ms = self._query_start_ms(start_time)

        ticket_ids = []
        method = getattr(
            self.siemplify,
            "get_alerts_ticket_ids_from_cases_closed_since_timestamp",
            None,
        )
        if callable(method):
            try:
                ticket_ids = _to_list(method(ts_ms, self.rule_generator))
                self._log(
                    "info",
                    "Closed-case ticket lookup since_ms=%s rule_generator=%s returned %d id(s).",
                    ts_ms,
                    self.rule_generator,
                    len(ticket_ids),
                )
            except Exception as exc:
                self._log(
                    "warning",
                    "get_alerts_ticket_ids_from_cases_closed_since_timestamp failed: %s",
                    exc,
                )

        for ticket_id in ticket_ids:
            ticket_key = str(ticket_id)
            if not ticket_key or ticket_key in seen_keys:
                continue
            cases = self._cases_from_ticket_id(ticket_key)
            if cases:
                for case_id, case_obj in cases:
                    key = f"case:{case_id}"
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    results.append((key, case_obj))
            else:
                case_obj = self._load_case(ticket_key)
                if case_obj is not None:
                    key = f"case:{ticket_key}"
                    seen_keys.add(key)
                    results.append((key, case_obj))
                else:
                    key = f"ticket:{ticket_key}"
                    seen_keys.add(key)
                    results.append((key, {"ticket_id": ticket_key}))

        for case_id in self._closed_case_ids(start_time):
            key = f"case:{case_id}"
            if key in seen_keys:
                continue
            case_obj = self._load_case(case_id)
            if case_obj is None:
                continue
            if not _case_is_flare(case_obj) and not extract_flare_uids_from_obj(case_obj):
                continue
            seen_keys.add(key)
            results.append((key, case_obj))

        self._log("info", "Found %d closed Flare case/alert payload(s).", len(results))
        return results

    def resolve_targets(self, closed_items: list) -> tuple:
        processed = self.state.get("processed_alerts") or {}
        pending: list = []
        seen: set = set()
        skipped = 0
        per_item: dict = {}

        for key, payload in closed_items:
            if key in processed:
                skipped += 1
                self._log("info", "Closed item %s already remediated — skipping.", key)
                continue

            uids = sorted(extract_flare_uids_from_obj(payload))
            if not uids:
                self._log(
                    "warning",
                    "Closed item %s had no extractable Flare UID — skipping",
                    key,
                )
                continue

            new_uids = [uid for uid in uids if uid not in seen]
            for uid in new_uids:
                seen.add(uid)
                pending.append(uid)
            per_item[key] = new_uids
            self._log(
                "info",
                "Closed Flare case found — key=%s flare_uids=%s",
                key,
                ", ".join(new_uids),
            )

        return pending, skipped, per_item

    def run_once(self) -> dict:
        start_time = self.get_query_start_time()
        current_run = utc_now_iso()
        checkpoint_label = (
            start_time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if start_time
            else "ALL_CLOSED_CASES"
        )

        self._log(
            "info",
            "Starting SOAR remediation sync (query_start=%s, rule_generator=%s).",
            checkpoint_label,
            self.rule_generator,
        )

        closed_items = self.fetch_closed_flare_cases(start_time)
        pending, skipped, per_item = self.resolve_targets(closed_items)

        result = {"applied": 0, "errors": []}
        if pending:
            self._log(
                "info",
                "Remediating %d Flare event(s) from %d closed item(s) (batch_size=%d).",
                len(pending),
                len(per_item),
                self.action_batch_size,
            )
            result = self.flare.remediate_events(
                pending, batch_size=self.action_batch_size
            )

        can_advance = not result["errors"] and (
            skipped > 0 or result["applied"] == len(pending) or not pending
        )

        new_checkpoint = None
        if can_advance:
            # Persist "now" so the next run only looks at cases closed after this sync.
            self.state["last_successful_check_timestamp"] = current_run
            new_checkpoint = current_run
            processed = self.state.setdefault("processed_alerts", {})
            for key, uids in per_item.items():
                processed[key] = {
                    "flare_uids": uids,
                    "action": "remediate",
                    "processed_at": current_run,
                    "status": "closed",
                }
            if len(processed) > 5000:
                items = sorted(
                    processed.items(),
                    key=lambda kv: kv[1].get("processed_at") or "",
                    reverse=True,
                )
                self.state["processed_alerts"] = dict(items[:4000])

        if result["errors"]:
            msg = (
                f"Remediation sync completed with errors: "
                f"{result['applied']} remediated, "
                f"{len(result['errors'])} batch error(s). Checkpoint not advanced."
            )
        elif not closed_items:
            msg = (
                "No closed Flare SOAR cases/alerts since "
                f"{checkpoint_label}."
            )
        elif not pending and skipped:
            msg = (
                f"All {skipped} closed item(s) already processed. "
                f"Checkpoint advanced to {new_checkpoint}."
            )
        elif not pending:
            msg = (
                f"No Flare UIDs extracted from {len(closed_items)} closed item(s). "
                f"Checkpoint {'advanced' if new_checkpoint else 'not advanced'}."
            )
        else:
            msg = (
                f"Remediation sync completed: {result['applied']} Flare event(s) "
                f"remediated from {len(closed_items)} closed SOAR item(s)."
            )

        self._log("info", msg)
        return {
            "message": msg,
            "remediated_count": result["applied"],
            "remediated_uids": pending[: result["applied"]] if result["applied"] else [],
            "alerts_checked": len(closed_items),
            "already_processed_skipped": skipped,
            "pending_remediation_count": len(pending),
            "checkpoint_used": checkpoint_label,
            "new_checkpoint_saved": new_checkpoint,
            "errors": result["errors"],
            "state": self.state,
        }


# Backwards-compatible alias
SecOpsRemediator = SoarRemediator
