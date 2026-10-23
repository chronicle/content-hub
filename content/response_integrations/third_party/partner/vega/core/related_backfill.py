"""Checkpoint and backfill state for related Vega alerts."""

from __future__ import annotations

import time

from .constants import (
    ENTITY_TYPE_ALERT,
    ENTITY_TYPE_INCIDENT,
    GRAPHQL_PAGE_SIZE,
    MAX_ALERTS_PER_CASE,
    RELATED_BATCH_VERSION,
)
from .mapping import (
    incident_alert_ids,
    incident_alert_stubs,
    index_alert_records,
    record_alert_ids,
    record_display_id,
    record_id,
    related_incident_ids,
)


def _drop_none(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if value is not None}


class RelatedBackfillMixin:
    def _incident_time_window(self, incident: dict) -> tuple[str, str]:
        """Shared createdAt / lastUpdated so related alerts stay one group."""
        start = str((incident or {}).get("createdAt") or "").strip()
        end = str((incident or {}).get("lastUpdated") or (incident or {}).get("updatedAt") or start).strip()
        return start, end

    def _incident_log_label(self, incident: dict) -> str:
        identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
        display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
        if display_id and display_id != identifier:
            return f"{display_id} ({identifier})"
        return identifier or display_id or "(unknown incident)"

    def _log_nested_counts(self, incidents: list[dict], step: str, note: str) -> None:
        self._log("info", "%s: %s incident(s). %s", step, len(incidents), note)
        for incident in incidents:
            nested = len(incident_alert_ids(incident))
            expected = self._incident_alerts_count(incident)
            gap = max(expected - nested, 0)
            self._log(
                "info",
                "%s — %s: alertsCount=%s, nested alert ids in hand=%s, ids still missing from the nested field=%s.",
                step,
                self._incident_log_label(incident),
                expected,
                nested,
                gap,
            )

    def _incident_alerts_count(self, incident: dict) -> int:
        try:
            return max(int((incident or {}).get("alertsCount") or 0), 0)
        except (TypeError, ValueError):
            return 0

    def _nested_alerts_are_short(self, incident: dict) -> bool:
        expected = self._incident_alerts_count(incident)
        return expected > len(incident_alert_ids(incident))

    def _expand_nested_alert_ids(self, incidents: list[dict]) -> list[dict]:
        """Replace a short nested alerts page with the by-id getIncidents list.

        The incident list returns alertsCount in full and only a page of nested
        alert ids. getIncidents(incidentIds) for that one incident returns every id.
        """
        expanded: list[dict] = []
        for incident in incidents:
            if not isinstance(incident, dict):
                continue
            if not self._nested_alerts_are_short(incident):
                expanded.append(incident)
                continue
            identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
            if not identifier:
                expanded.append(incident)
                continue
            # A prior run can mark this alertsCount settled after seeing only
            # the short list page. Drop that so the by-id ids are read again.
            self._settled_related.pop(identifier, None)
            current = len(incident_alert_ids(incident))
            try:
                full = self.manager.get_incident(identifier)
            except Exception as exc:
                self._log(
                    "warning",
                    "Unable to load full alert ids for Vega incident %s: %s",
                    identifier,
                    exc,
                )
                expanded.append(incident)
                continue
            if not isinstance(full, dict):
                expanded.append(incident)
                continue
            full_ids = incident_alert_ids(full)
            if len(full_ids) <= current:
                expanded.append(incident)
                continue
            merged = dict(incident)
            merged["alerts"] = full.get("alerts")
            if full.get("alertsCount") is not None:
                merged["alertsCount"] = full.get("alertsCount")
            self._log(
                "info",
                "Vega incident %s alert ids expanded from %s to %s via getIncidents(incidentIds).",
                identifier,
                current,
                len(full_ids),
            )
            expanded.append(merged)
        return expanded

    def _needs_related_scan(self, incident: dict) -> bool:
        """True until a full related-alert scan has run for this alertsCount."""
        identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
        if not identifier:
            return False
        if identifier in self._open_related:
            return True
        expected = self._incident_alerts_count(incident)
        settled_at = self._settled_related.get(identifier)
        if settled_at is not None and expected <= settled_at:
            return False
        return self._nested_alerts_are_short(incident)

    def _remember_open_incident(self, incident: dict, have: int) -> None:
        identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
        if not identifier:
            return
        self._open_related[identifier] = {
            "expected": self._incident_alerts_count(incident),
            "display_id": record_display_id(incident, ENTITY_TYPE_INCIDENT),
            "have": max(int(have or 0), 0),
        }

    def _backfill_variables(self, window: dict) -> dict:
        """Related-alert scan with no severity, status, or verdict filter.

        getAlerts has no incident-id argument. Pages are limited to alerts that
        have a related incident, then matched to the open incidents here.
        """
        lookup = self._id_lookup_window(window)
        return _drop_none({
            "hasRelatedIncidents": True,
            "from": lookup.get("from"),
            "to": lookup.get("to"),
            "updatedFrom": lookup.get("updated_from"),
            "updatedTo": lookup.get("updated_to"),
        })

    def _backfill_related_index(
        self,
        incidents: list[dict],
        related_index: dict[str, dict],
        window: dict,
    ) -> dict[str, dict]:
        """Page related alerts until each short incident reaches alertsCount.

        A timeout saves the scan offset. The next run continues from there
        instead of marking the incident finished after the first nested page.
        """
        tracked = [item for item in incidents if self._needs_related_scan(item)]
        if not tracked:
            self._related_scan_offset = 0
            return related_index
        new_ids = [
            record_id(incident, ENTITY_TYPE_INCIDENT)
            for incident in tracked
            if record_id(incident, ENTITY_TYPE_INCIDENT) not in self._open_ids_at_start
        ]
        if new_ids:
            self._related_scan_offset = 0
        wanted: dict[str, str] = {}
        for incident in tracked:
            identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
            display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
            if identifier:
                wanted[identifier] = identifier
            if display_id:
                wanted[display_id] = identifier
        self._log(
            "info",
            "Nested alerts list is short for %s incident(s); paging related alerts from offset %s.",
            len(tracked),
            self._related_scan_offset,
        )
        matched: list[dict] = []
        seen_match: set[str] = set()
        offset = self._related_scan_offset
        page_size = max(1, int(GRAPHQL_PAGE_SIZE))
        variables = self._backfill_variables(window)
        scan_finished = False
        while True:
            if self._deadline_reached():
                self._related_scan_incomplete = True
                break
            try:
                page = self.manager.get_alerts(
                    variables,
                    page_size,
                    deadline_monotonic=self._deadline,
                    start_offset=offset,
                )
                self._mark_if_truncated()
            except Exception as exc:
                self._related_scan_incomplete = True
                self._log("warning", "Unable to backfill related Vega alerts: %s", exc)
                break
            page = [item for item in (page or []) if isinstance(item, dict)]
            if not page:
                scan_finished = True
                break
            for alert in page:
                owner_ids = [wanted[item] for item in related_incident_ids(alert) if item in wanted]
                if not owner_ids:
                    continue
                alert_id = record_id(alert, ENTITY_TYPE_ALERT)
                if not alert_id or alert_id in seen_match:
                    continue
                seen_match.add(alert_id)
                matched.append(alert)
            offset += len(page)
            self._related_scan_offset = offset
            if getattr(self.manager, "last_fetch_truncated", False) or self._deadline_reached():
                self._related_scan_incomplete = True
                break
            if len(page) < page_size:
                scan_finished = True
                break
        if scan_finished:
            self._related_scan_incomplete = False
            self._related_scan_offset = 0
        extra = index_alert_records(matched)
        merged = dict(related_index)
        for key, alert in extra.items():
            merged.setdefault(key, alert)
        self._log(
            "info",
            "Backfill matched %s related Vega alert(s) for short incident lists (scan_offset=%s incomplete=%s).",
            len(seen_match),
            self._related_scan_offset,
            self._related_scan_incomplete,
        )
        return merged

    def _incident_ingested_key(self, incident: dict) -> str:
        identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
        return f"incident:{identifier}" if identifier else ""

    def _new_related_alert_ids(self, incident: dict, ingested_set: set[str]) -> list[str]:
        """Alert IDs from this incident that are not already in the checkpoint."""
        ids: list[str] = []
        seen: set[str] = set()
        for stub in incident_alert_stubs(incident):
            keys = record_alert_ids(stub)
            if any(key in ingested_set for key in keys):
                continue
            for key in keys:
                if key not in seen:
                    seen.add(key)
                    ids.append(key)
        return ids

    def _load_related_backfill(self, state: dict) -> None:
        saved = state.get("related_backfill")
        if not isinstance(saved, dict):
            saved = {}
            # Checkpoints written before related-alert resume have no scan
            # state. Reload those incidents once so a short nested page is
            # not left finished.
            self._upgrade_incident_ids = [
                item.split(":", 1)[1]
                for item in list(state.get("ingested_ids") or [])
                if str(item).startswith("incident:") and ":" in str(item)
            ]
        else:
            self._upgrade_incident_ids = [
                str(item) for item in list(saved.get("upgrade_ids") or []) if str(item).strip()
            ]
        try:
            batch_version = int(saved.get("batch_version") or 0)
        except (TypeError, ValueError):
            batch_version = 0
        # Older checkpoints marked every related id sent after one large
        # return. SecOps kept only part of that return, so send those again.
        self._replay_related = batch_version < RELATED_BATCH_VERSION
        if self._replay_related:
            self._next_related_batch = {}
            self._related_batch_filled = {}
        else:
            next_batch: dict[str, int] = {}
            for key, value in dict(saved.get("next_related_batch") or {}).items():
                try:
                    next_batch[str(key)] = max(int(value), 1)
                except (TypeError, ValueError):
                    continue
            filled: dict[str, int] = {}
            for key, value in dict(saved.get("related_batch_filled") or {}).items():
                try:
                    filled[str(key)] = max(int(value), 0)
                except (TypeError, ValueError):
                    continue
            self._next_related_batch = next_batch
            self._related_batch_filled = filled
        try:
            offset = int(saved.get("offset") or 0)
        except (TypeError, ValueError):
            offset = 0
        self._related_scan_offset = max(offset, 0)
        self._related_scan_incomplete = False
        open_related: dict[str, dict] = {}
        for key, value in dict(saved.get("open") or {}).items():
            if isinstance(value, dict):
                open_related[str(key)] = dict(value)
        self._open_related = open_related
        settled: dict[str, int] = {}
        for key, value in dict(saved.get("settled") or {}).items():
            try:
                settled[str(key)] = max(int(value), 0)
            except (TypeError, ValueError):
                continue
        self._settled_related = {} if self._replay_related else settled
        self._open_ids_at_start = set(self._open_related)

    def _include_open_incidents(self, incidents: list[dict]) -> list[dict]:
        """Re-read incidents whose related-alert scan stopped early."""
        present = {record_id(item, ENTITY_TYPE_INCIDENT) for item in incidents if record_id(item, ENTITY_TYPE_INCIDENT)}
        pending_ids = list(self._open_related) + [
            item for item in self._upgrade_incident_ids if item not in self._open_related
        ]
        for incident_id in pending_ids:
            if incident_id in present or self._deadline_reached():
                if incident_id in present:
                    self._upgrade_incident_ids = [item for item in self._upgrade_incident_ids if item != incident_id]
                continue
            try:
                record = self.manager.get_incident(incident_id)
            except Exception as exc:
                self._log(
                    "warning",
                    "Unable to reload open Vega incident %s: %s",
                    incident_id,
                    exc,
                )
                continue
            if not isinstance(record, dict) or not record_id(record, ENTITY_TYPE_INCIDENT):
                self._upgrade_incident_ids = [item for item in self._upgrade_incident_ids if item != incident_id]
                continue
            incidents.append(record)
            present.add(incident_id)
            self._upgrade_incident_ids = [item for item in self._upgrade_incident_ids if item != incident_id]
        return incidents

    def _release_oversized_related(
        self,
        incident: dict,
        ingested: list[str],
        ingested_set: set[str],
    ) -> None:
        """Forget a one-shot send that was larger than SecOps keeps."""
        if not self._replay_related:
            return
        release: set[str] = set()
        for stub in incident_alert_stubs(incident):
            for key in record_alert_ids(stub):
                if key in ingested_set:
                    release.add(key)
        if not release:
            return
        ingested_set.difference_update(release)
        ingested[:] = [item for item in ingested if item not in release]
        label = record_display_id(incident, ENTITY_TYPE_INCIDENT) or record_id(incident, ENTITY_TYPE_INCIDENT)
        self._log(
            "info",
            "Vega incident %s: an earlier run marked %s related alert(s) as "
            "sent. getAlerts will be called for each of them and each one "
            "will be packaged.",
            label,
            len(release),
        )

    def _note_related_progress(self, incident: dict, added: int) -> None:
        """Keep an incident open until every known related alert is packaged."""
        identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
        if not identifier:
            return
        known = len(incident_alert_ids(incident))
        expected = max(self._incident_alerts_count(incident), known)
        previous = int((self._open_related.get(identifier) or {}).get("have") or 0)
        have = previous + max(int(added or 0), 0)
        short = self._nested_alerts_are_short(incident)
        if have >= expected and not short:
            self._open_related.pop(identifier, None)
            self._settled_related[identifier] = expected
            return
        tracked = identifier in self._open_related or identifier in self._open_ids_at_start or short or have < known
        if not tracked:
            return
        unfinished = self._related_scan_incomplete or self._incomplete or self._deadline_reached()
        if have < expected and unfinished:
            self._remember_open_incident(incident, have)
            self._log(
                "info",
                "Vega incident %s packaged %s of %s related alert(s) this run. "
                "The connector time limit stopped the rest. The next run "
                "continues in batches of %s.",
                identifier,
                have,
                expected,
                MAX_ALERTS_PER_CASE,
            )
            return
        if have < expected and short:
            self._log(
                "warning",
                "Vega incident %s related-alert scan finished with %s of %s alert(s).",
                identifier,
                have,
                expected,
            )
        self._open_related.pop(identifier, None)
        self._settled_related[identifier] = expected
