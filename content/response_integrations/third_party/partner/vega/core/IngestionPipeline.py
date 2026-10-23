"""Fetch Vega alerts/incidents, enrich, checkpoint, and return records.

Connector flow
--------------
1. The connector reads instance configuration (entities, lookback, filters,
   Has Related Incidents) and constructs this pipeline.
2. `run()` computes the time window from checkpoint + lookback/backfill.
   If a cycle stops early to avoid connector timeout, the checkpoint stores
   the last packaged record timestamp (not the current time) so the next
   run continues the remaining incidents, alerts, and events.
3. Vega Entities to Fetch and Has Related Incidents together decide what is
   packaged. Each emitted record becomes one SOAR alert inside a case:

   Incidents + Alerts
     Yes,No: incident-only case, related alerts sharing one grouping id,
             unrelated alerts as their own cases.
     Yes:    incident-only case plus related alerts on that grouping id;
             skip unrelated alerts.
     No:     incident-only case; unrelated alerts as their own cases.

   Incidents only (Yes, No, or Yes,No): incident-only cases. Do not fetch
     related or unrelated alerts as their own cases.

   Fetch Related Alert Metadata: when enabled, each incident's vega_alerts
   field is the full getAlerts record for every nested alert id (up to 1000
   UUIDs per request; the response is paged until those alerts return). When
   disabled, vega_alerts is only alertId, name, and createdAt from
   getIncidents. This does not create related-alert cases.

   Alerts only
     Yes,No: standalone cases for related alerts and unrelated alerts.
     Yes:    standalone cases for related alerts only.
     No:     standalone cases for unrelated alerts only.

4. Records are packaged into SOAR AlertInfo objects by AlertPackager.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


import logging
import time
from datetime import datetime

from .constants import (
    ALERT_EVENTS_ID_BATCH,
    ALERT_ID_LOOKUP_BATCH,
    ALERT_ID_LOOKUP_FROM,
    ALERT_METADATA_ID_BATCH,
    ENTITY_TYPE_ALERT,
    ENTITY_TYPE_INCIDENT,
    GRAPHQL_PAGE_SIZE,
    INGESTED_ID_CAP,
    MAX_ALERTS_PER_CASE,
    RELATED_BATCH_VERSION,
    SOAR_ALERT_TYPE_ALERT,
    SOAR_ALERT_TYPE_INCIDENT,
    TEST_RUN_MAX_FETCH,
)
from .mapping import (
    alert_grouping_id,
    case_display_name,
    collect_label_tags,
    incident_alert_ids,
    incident_alert_stubs,
    incident_alert_summary,
    incident_case_title,
    incident_grouping_id,
    index_alert_records,
    is_graphql_alert_id,
    merge_related_alert,
    record_alert_ids,
    record_display_id,
    record_id,
    record_label_tags,
    record_name,
    record_timestamp,
    related_incident_ids,
    set_soar_meta,
)
from .utils import (
    compute_time_window,
    parse_backfill_days,
    parse_iso_timestamp,
    parse_lookback_minutes,
    resolve_alert_filters,
    resolve_entities,
    resolve_incident_filters,
    safe_log,
    to_iso,
)

from .case_emission import CaseEmissionMixin
from .related_backfill import RelatedBackfillMixin, _drop_none

logger = logging.getLogger(__name__)



class IngestionPipeline(CaseEmissionMixin, RelatedBackfillMixin):
    """Poll Vega and return packages that match SecOps Case > Alert > Event."""

    def __init__(
        self,
        manager: Any,
        entities_raw: str,
        lookback_minutes: str,
        backfill_days: str,
        alert_severities: str = "",
        alert_statuses: str = "",
        alert_verdicts: str = "",
        has_related: str = "Yes,No",
        incident_severities: str = "",
        incident_user_statuses: str = "",
        incident_investigation_statuses: str = "",
        incident_verdicts: str = "",
        fetch_related_alert_metadata: bool = False,
        max_fetch: int | None = None,
        logger_instance: Any = None,
    ) -> None:
        self.manager = manager
        self.entities = resolve_entities(entities_raw)
        self.max_fetch = max_fetch
        self.lookback_minutes = parse_lookback_minutes(lookback_minutes)
        self.backfill_days = parse_backfill_days(backfill_days)
        self.alert_filters = resolve_alert_filters({
            "alert_severities": alert_severities,
            "alert_statuses": alert_statuses,
            "alert_verdicts": alert_verdicts,
            "has_related": has_related,
        })
        self.fetch_related_alert_metadata = bool(fetch_related_alert_metadata)
        self.incident_filters = resolve_incident_filters({
            "incident_severities": incident_severities,
            "incident_user_statuses": incident_user_statuses,
            "incident_investigation_statuses": incident_investigation_statuses,
            "incident_verdicts": incident_verdicts,
        })
        self.logger = logger_instance or logger
        self._incident_cache: dict[str, SingleJson] = {}
        self._incomplete = False
        self._progress_ts: datetime | None = None
        self._deadline: float | None = None
        self._open_related: dict[str, SingleJson] = {}
        self._settled_related: dict[str, int] = {}
        self._open_ids_at_start: set[str] = set()
        self._upgrade_incident_ids: list[str] = []
        self._replay_related = False
        self._related_scan_offset = 0
        self._related_scan_incomplete = False
        self._next_related_batch: dict[str, int] = {}
        self._related_batch_filled: dict[str, int] = {}

    def _log(self, level: str, msg: str, *args) -> None:
        safe_log(self.logger, level, msg, *args)

    def _alert_variables(
        self,
        window: SingleJson,
        has_related: bool | None,
        alert_ids: list[str | None] = None,
        vega_alert_ids: list[str | None] = None,
        include_time: bool = True,
    ) -> SingleJson:
        payload: SingleJson = {}
        if not (alert_ids or vega_alert_ids):
            filters = self.alert_filters
            payload = {
                "alertSeverities": filters["severities"],
                "statuses": filters["statuses"],
                "alertVerdicts": filters["verdicts"],
            }
        # ID lookups skip connector alert filters so nested related alerts
        # keep their Vega labels instead of being replaced by stubs.
        if alert_ids:
            payload["alertIds"] = alert_ids
        if vega_alert_ids:
            payload["vegaAlertIds"] = vega_alert_ids
        if alert_ids or vega_alert_ids:
            # Keep the ingest time window. Vega getAlerts returns 0 rows when
            # alertIds are sent without from/to/updatedFrom/updatedTo.
            if include_time:
                payload["from"] = (window or {}).get("from")
                payload["to"] = (window or {}).get("to")
                payload["updatedFrom"] = (window or {}).get("updated_from")
                payload["updatedTo"] = (window or {}).get("updated_to")
            return _drop_none(payload)
        payload["hasRelatedIncidents"] = has_related
        payload["from"] = (window or {}).get("from")
        payload["to"] = (window or {}).get("to")
        payload["updatedFrom"] = (window or {}).get("updated_from")
        payload["updatedTo"] = (window or {}).get("updated_to")
        return _drop_none(payload)

    def _incident_variables(self, window: SingleJson) -> SingleJson:
        filters = self.incident_filters
        return _drop_none({
            "severities": filters["severities"],
            "userStatuses": filters["user_statuses"],
            "investigationStatuses": filters["investigation_statuses"],
            "verdicts": filters["verdicts"],
            "from": window.get("from"),
            "to": window.get("to"),
            "updatedFrom": window.get("updated_from"),
            "updatedTo": window.get("updated_to"),
        })

    def _enrich_incident(self, record: SingleJson) -> SingleJson:
        identifier = record_id(record, ENTITY_TYPE_INCIDENT)
        if not identifier:
            return record
        try:
            events = self.manager.get_all_incident_timeline(identifier, deadline_monotonic=self._deadline)
            self._mark_if_truncated()
            record = dict(record)
            record["timeline"] = events
            self._log(
                "info",
                "Fetched %s timeline event(s) for Vega incident %s.",
                len(events),
                identifier,
            )
        except Exception as exc:
            self._log(
                "warning",
                "Unable to fetch timeline for Vega incident %s: %s",
                identifier,
                exc,
            )
        return record

    def _now(self) -> float:
        return time.monotonic()

    def _deadline_reached(self) -> bool:
        return self._deadline is not None and self._now() >= self._deadline

    def _mark_if_truncated(self) -> None:
        if getattr(self.manager, "last_fetch_truncated", False):
            self._incomplete = True

    def _should_stop(self, collected: int) -> bool:
        if self._remaining(collected) == 0:
            return True
        if not self._deadline_reached():
            return False
        if not self._incomplete:
            self._incomplete = True
            resume = to_iso(self._progress_ts) if self._progress_ts else "the current watermark"
            self._log(
                "info",
                "Stopping ingest before connector timeout so this cycle can "
                "package cases and save the watermark. Remaining Vega records "
                "resume next run from %s.",
                resume,
            )
        return True

    def _note_progress(self, record: SingleJson) -> None:
        parsed = parse_iso_timestamp(record_timestamp(record))
        if parsed is None:
            return
        if self._progress_ts is None or parsed > self._progress_ts:
            self._progress_ts = parsed

    def _sort_by_timestamp(self, rows: list[SingleJson]) -> list[SingleJson]:
        return sorted(rows, key=lambda row: record_timestamp(row) or "")

    def _preferred_event_id(self, record: SingleJson) -> str:
        """UUID for getAlertsEvents(alertIds), otherwise the first candidate."""
        candidates = record_alert_ids(record)
        for candidate in candidates:
            if is_graphql_alert_id(candidate):
                return candidate
        return candidates[0] if candidates else ""

    def _lookup_prefetched_events(self, events_by_id: dict[str, list], alert_id: str) -> list | None:
        if alert_id in events_by_id:
            return list(events_by_id.get(alert_id) or [])
        if not is_graphql_alert_id(alert_id):
            return None
        for key, value in events_by_id.items():
            if is_graphql_alert_id(key) and key.casefold() == alert_id.casefold():
                return list(value or [])
        return None

    def _apply_prefetched_events(self, record: SingleJson, events_by_id: dict[str, list]) -> SingleJson:
        """Attach only the events fetched for this alert's own id."""
        record = dict(record)
        candidates = record_alert_ids(record)
        events: list = []
        for alert_id in candidates:
            matched = self._lookup_prefetched_events(events_by_id, alert_id)
            if matched is None:
                continue
            events = matched
            break
        record["alert_events"] = events
        return record

    def _fetch_events_for_alerts(self, alerts: list[SingleJson]) -> dict[str, list]:
        """Load events for these alerts. UUID ids are batched (max 10 per call)."""
        query_ids: list[str] = []
        seen: set[str] = set()
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            alert_id = self._preferred_event_id(alert)
            if not alert_id or alert_id in seen:
                continue
            seen.add(alert_id)
            query_ids.append(alert_id)
        if not query_ids:
            return {}
        batch_fetch = getattr(self.manager, "get_all_alerts_events", None)
        if not callable(batch_fetch):
            return self._fetch_events_one_by_one(alerts)
        try:
            fetched = batch_fetch(query_ids, deadline_monotonic=self._deadline) or {}
            self._mark_if_truncated()
        except Exception as exc:
            self._log(
                "warning",
                "Unable to batch-fetch Vega alert events for %s alert(s): %s",
                len(query_ids),
                exc,
            )
            return self._fetch_events_one_by_one(alerts)
        events_by_id: dict[str, list] = {}
        if isinstance(fetched, dict):
            for key, value in fetched.items():
                alert_id = str(key or "").strip()
                if alert_id:
                    events_by_id[alert_id] = list(value or [])
        return events_by_id

    def _fetch_events_one_by_one(self, alerts: list[SingleJson]) -> dict[str, list]:
        events_by_id: dict[str, list] = {}
        for alert in alerts:
            if not isinstance(alert, dict):
                continue
            try:
                enriched = self._enrich_alert(alert)
            except Exception as exc:
                identifier = record_id(alert, ENTITY_TYPE_ALERT)
                self._log(
                    "warning",
                    "Unable to fetch events for Vega alert %s: %s",
                    identifier,
                    exc,
                )
                enriched = dict(alert)
                enriched["alert_events"] = []
            events = list(enriched.get("alert_events") or [])
            for candidate in record_alert_ids(alert):
                events_by_id[candidate] = events
        return events_by_id

    def _enrich_alert(self, record: SingleJson) -> SingleJson:
        # Child Vega Alert Events live on the Vega Alert, not the incident.
        record = dict(record)
        candidates = record_alert_ids(record)
        if not candidates:
            record.setdefault("alert_events", [])
            return record
        events: list = []
        for alert_id in candidates:
            try:
                events = self.manager.get_all_alert_events(alert_id, deadline_monotonic=self._deadline)
                self._mark_if_truncated()
            except Exception as exc:
                self._log(
                    "warning",
                    "Unable to fetch events for Vega alert %s: %s",
                    alert_id,
                    exc,
                )
                continue
            break
        record["alert_events"] = events
        return record

    def _remaining(self, collected: int) -> int | None:
        if self.max_fetch is None:
            return None
        leftover = self.max_fetch - collected
        return leftover if leftover > 0 else 0

    def _mark_ingested(self, ingested: list[str], ingested_set: set[str], identifier: str) -> None:
        if identifier in ingested_set:
            return
        ingested_set.add(identifier)
        ingested.append(identifier)

    def _cache_incident(self, incident: SingleJson) -> None:
        identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
        if identifier:
            self._incident_cache[identifier] = incident
        display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
        if display_id:
            self._incident_cache[display_id] = incident

    def _id_lookup_window(self, window: SingleJson) -> SingleJson:
        """Wide created/updated range so related alerts older than the ingest window still resolve."""
        end = (window or {}).get("to") or (window or {}).get("updated_to") or (window or {}).get("end")
        return {
            "from": ALERT_ID_LOOKUP_FROM,
            "to": end,
            "updated_from": ALERT_ID_LOOKUP_FROM,
            "updated_to": end,
        }

    def _metadata_lookup_ids(self, incident: SingleJson) -> list[str]:
        """One id per nested alert. UUID alertId is preferred for getAlerts."""
        ids: list[str] = []
        seen: set[str] = set()
        for stub in incident_alert_stubs(incident):
            candidates = record_alert_ids(stub)
            chosen = ""
            for candidate in candidates:
                if is_graphql_alert_id(candidate):
                    chosen = candidate
                    break
            if not chosen and candidates:
                chosen = candidates[0]
            if not chosen or chosen in seen:
                continue
            seen.add(chosen)
            ids.append(chosen)
        return ids

    def _ingest_incidents(
        self,
        window: SingleJson,
        records: list[tuple[str, SingleJson]],
        ingested: list[str],
        ingested_set: set[str],
        include_related: bool = True,
    ) -> None:
        """Fetch Vega incidents and optionally nest related alerts in the case."""
        remaining = self._remaining(len(records))
        if remaining == 0 or self._should_stop(len(records)):
            return
        try:
            incidents = self.manager.get_incidents(
                self._incident_variables(window),
                remaining,
                deadline_monotonic=self._deadline,
            )
            self._mark_if_truncated()
        except Exception as exc:
            self._incomplete = True
            self._log("error", "Unable to fetch Vega incidents: %s", exc)
            return
        incidents = self._sort_by_timestamp([item for item in incidents if isinstance(item, dict)])
        self._log_nested_counts(
            incidents,
            "Step 1 — incident list",
            "These counts are from the list query. A short nested alerts field is reloaded by id in the next step.",
        )
        incidents = self._include_open_incidents(incidents)
        incidents = self._expand_nested_alert_ids(incidents)
        self._log_nested_counts(
            incidents,
            "Step 2 — nested alert ids",
            "These are the ids that will be used. alertsCount is Vega's "
            "total; nested ids is how many ids are actually in hand.",
        )
        if include_related and self._replay_related:
            for incident in incidents:
                self._release_oversized_related(incident, ingested, ingested_set)
        self._log("info", "Fetched %s Vega incident(s).", len(incidents))
        related_index: dict[str, SingleJson] = {}
        if include_related and incidents and not self._should_stop(len(records)):
            all_alert_ids: list[str] = []
            for incident in incidents:
                pending = self._pending_stubs(incident, ingested_set)
                nested = len(incident_alert_ids(incident))
                skipped = max(len(self._ordered_stubs(incident)) - len(pending), 0)
                batches = (len(self._ordered_stubs(incident)) + MAX_ALERTS_PER_CASE - 1) // MAX_ALERTS_PER_CASE
                self._log(
                    "info",
                    "Step 3 — %s: nested ids=%s, already checkpointed=%s, "
                    "getAlerts this run=%s, batches of %s=%s. "
                    "Every batch is sent in this run.",
                    self._incident_log_label(incident),
                    nested,
                    skipped,
                    len(pending),
                    MAX_ALERTS_PER_CASE,
                    batches if self._ordered_stubs(incident) else 0,
                )
                all_alert_ids.extend(self._stub_lookup_ids(pending))
            self._log(
                "info",
                "Step 3 — getAlerts will be called for %s id(s) this run, %s ids per call, limit %s.",
                len(all_alert_ids),
                ALERT_ID_LOOKUP_BATCH,
                ALERT_ID_LOOKUP_BATCH,
            )
            related_index = self._fetch_alerts_by_ids(all_alert_ids, window)
            related_index = self._backfill_related_index(incidents, related_index, window)
        for incident in incidents:
            if self._should_stop(len(records)):
                break
            identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
            if not identifier:
                continue
            already_ingested = self._incident_ingested_key(incident) in ingested_set
            pending_related = self._new_related_alert_ids(incident, ingested_set) if include_related else []
            if already_ingested and not pending_related and not self._needs_related_scan(incident):
                continue
            if not already_ingested:
                incident = self._enrich_incident(incident)
                incident = self._attach_vega_alerts(incident, window)
            self._cache_incident(incident)
            related = self._resolve_related_alerts(incident, related_index) if include_related else []
            self._log(
                "info",
                "Vega incident %s: found %s related alert id(s)%s.",
                identifier,
                len(related),
                "" if include_related else " (not nested into cases)",
            )
            before = len(records)
            self._emit_incident_cases(incident, related, records, ingested, ingested_set)
            if include_related:
                added = sum(1 for kind, _record in records[before:] if kind == ENTITY_TYPE_ALERT)
                self._note_related_progress(incident, added)

    def _append_standalone_alert(
        self,
        alert: SingleJson,
        records: list[tuple[str, SingleJson]],
        ingested: list[str],
        ingested_set: set[str],
        events_by_id: dict[str, list[SingleJson]] | None = None,
    ) -> bool:
        if self._should_stop(len(records)):
            return False
        identifier = record_id(alert, ENTITY_TYPE_ALERT)
        if not identifier or identifier in ingested_set:
            return False
        if events_by_id is not None:
            enriched = self._apply_prefetched_events(alert, events_by_id)
        else:
            enriched = self._enrich_alert(alert)
        packaged = set_soar_meta(
            enriched,
            soar_alert_type=SOAR_ALERT_TYPE_ALERT,
            grouping_id=alert_grouping_id(identifier),
            case_tags=collect_label_tags(alert),
            case_title=case_display_name(alert, ENTITY_TYPE_ALERT),
            incident_id="",
            is_incident_case=False,
        )
        records.append((ENTITY_TYPE_ALERT, packaged))
        self._mark_ingested(ingested, ingested_set, identifier)
        self._note_progress(packaged)
        return True

    def _ingest_standalone_alerts(
        self,
        window: SingleJson,
        records: list[tuple[str, SingleJson]],
        ingested: list[str],
        ingested_set: set[str],
        has_related: bool,
        label: str,
    ) -> None:
        """One SOAR case per Vega alert (related or unrelated, never nested)."""
        remaining = self._remaining(len(records))
        if remaining == 0 or self._should_stop(len(records)):
            return
        try:
            alerts = self.manager.get_alerts(
                self._alert_variables(window, has_related),
                remaining,
                deadline_monotonic=self._deadline,
            )
            self._mark_if_truncated()
        except Exception as exc:
            self._incomplete = True
            self._log("error", "Unable to fetch %s Vega alerts: %s", label, exc)
            return
        alerts = self._sort_by_timestamp([item for item in alerts if isinstance(item, dict)])
        self._log("info", "Fetched %s %s Vega alert(s).", len(alerts), label)
        batch_size = max(1, int(ALERT_EVENTS_ID_BATCH))
        index = 0
        while index < len(alerts):
            if self._should_stop(len(records)):
                break
            window = alerts[index : index + batch_size]
            pending = [
                alert
                for alert in window
                if record_id(alert, ENTITY_TYPE_ALERT) and record_id(alert, ENTITY_TYPE_ALERT) not in ingested_set
            ]
            remaining = self._remaining(len(records))
            if remaining is not None:
                pending = pending[:remaining]
            events_by_id = self._fetch_events_for_alerts(pending) if pending else {}
            stop = False
            for alert in window:
                if not self._append_standalone_alert(
                    alert,
                    records,
                    ingested,
                    ingested_set,
                    events_by_id=events_by_id,
                ):
                    if self._should_stop(len(records)):
                        stop = True
                        break
            if stop:
                break
            index += batch_size

    def _ingest_plan(self) -> SingleJson:
        """Map Vega Entities + Has Related Incidents to fetch/package behavior."""
        fetch_alerts = "Alerts" in self.entities
        fetch_incidents = "Incidents" in self.entities
        has_related = self.alert_filters["has_related"]
        want_related = has_related is not False
        want_unrelated = has_related is not True
        return {
            "fetch_incidents": fetch_incidents,
            "nest_related_alerts": fetch_incidents and fetch_alerts and want_related,
            "standalone_related_alerts": fetch_alerts and not fetch_incidents and want_related,
            "standalone_unrelated_alerts": fetch_alerts and want_unrelated,
            "has_related": has_related,
        }

    def _append_sample_incidents(
        self,
        window: SingleJson,
        records: list[tuple[str, SingleJson]],
        remaining: int,
        incidents: list[SingleJson] | None = None,
    ) -> int:
        if remaining <= 0:
            return 0
        if incidents is None:
            incidents = self.manager.get_incidents(self._incident_variables(window), remaining)
        added = 0
        for incident in incidents:
            if added >= remaining:
                break
            if not isinstance(incident, dict):
                continue
            identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
            if not identifier:
                continue
            display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
            incident = self._attach_vega_alerts(incident, window)
            packaged = set_soar_meta(
                incident,
                soar_alert_type=SOAR_ALERT_TYPE_INCIDENT,
                grouping_id=incident_grouping_id(identifier),
                case_tags=collect_label_tags(incident),
                case_title=incident_case_title(incident),
                grouping_time=record_timestamp(incident),
                incident_id=identifier,
                incident_display_id=display_id,
                incident_name=record_name(incident),
                is_incident_case=True,
                is_related_batch=False,
                case_part=0,
            )
            records.append((ENTITY_TYPE_INCIDENT, packaged))
            added += 1
        return added

    def _append_sample_alerts(
        self,
        window: SingleJson,
        records: list[tuple[str, SingleJson]],
        remaining: int,
        has_related: bool,
    ) -> int:
        if remaining <= 0:
            return 0
        alerts = self.manager.get_alerts(self._alert_variables(window, has_related), remaining)
        added = 0
        for alert in alerts:
            if added >= remaining:
                break
            if not isinstance(alert, dict):
                continue
            identifier = record_id(alert, ENTITY_TYPE_ALERT)
            if not identifier:
                continue
            packaged = set_soar_meta(
                alert,
                soar_alert_type=SOAR_ALERT_TYPE_ALERT,
                grouping_id=alert_grouping_id(identifier),
                case_tags=collect_label_tags(alert),
                case_title=case_display_name(alert, ENTITY_TYPE_ALERT),
                incident_id="",
                is_incident_case=False,
            )
            records.append((ENTITY_TYPE_ALERT, packaged))
            added += 1
        return added

    def _related_alert_count(self, incidents: list[SingleJson]) -> int:
        """Count unique nested alerts on incidents (not getAlerts time-window).

        Related Vega alerts are often older than the ingest window, so
        getAlerts(hasRelatedIncidents=true) in that window returns 0.
        """
        seen: set[str] = set()
        alerts_count_sum = 0
        for incident in incidents:
            for alert_id in incident_alert_ids(incident):
                seen.add(alert_id)
            raw = incident.get("alertsCount")
            try:
                alerts_count_sum += max(int(raw or 0), 0)
            except (TypeError, ValueError):
                pass
        return len(seen) if seen else alerts_count_sum

    def preview(self, sample_limit: int = TEST_RUN_MAX_FETCH) -> SingleJson:
        """Count matching Vega records and return sample packages without ingest.

        Does not fetch timelines or alert events, and does not write a checkpoint.
        When Fetch Related Alert Metadata is enabled, sample incidents include
        full getAlerts rows in vega_alerts.
        Counts follow Vega Entities to Fetch and Has Related Incidents.
        """
        window = compute_time_window({}, self.backfill_days, self.lookback_minutes)
        plan = self._ingest_plan()
        include_incidents = bool(plan["fetch_incidents"])
        include_related = bool(plan["nest_related_alerts"] or plan["standalone_related_alerts"])
        include_unrelated = bool(plan["standalone_unrelated_alerts"])
        incident_count = 0
        related_count = 0
        unrelated_count = 0
        incidents: list[SingleJson] = []
        if include_incidents:
            incidents = [
                item for item in self.manager.get_incidents(self._incident_variables(window)) if isinstance(item, dict)
            ]
            incident_count = len(incidents)
        if include_related:
            if include_incidents:
                related_count = self._related_alert_count(incidents)
            else:
                related_count = self.manager.count_alerts(self._alert_variables(self._id_lookup_window(window), True))
        if include_unrelated:
            unrelated_count = self.manager.count_alerts(self._alert_variables(window, False))
        remaining = max(1, int(sample_limit))
        records: list[tuple[str, SingleJson]] = []
        if include_incidents:
            remaining -= self._append_sample_incidents(window, records, remaining, incidents=incidents)
        if remaining and include_related:
            remaining -= self._append_sample_alerts(window, records, remaining, True)
        if remaining and include_unrelated:
            self._append_sample_alerts(window, records, remaining, False)
        return {
            "incident_count": incident_count,
            "related_alert_count": related_count,
            "unrelated_alert_count": unrelated_count,
            "total_alert_count": related_count + unrelated_count,
            "include_incidents": include_incidents,
            "include_related": include_related,
            "include_unrelated": include_unrelated,
            "records": records,
            "window": window,
        }

    def run(
        self,
        checkpoint: SingleJson | None = None,
        deadline_monotonic: float | None = None,
    ) -> SingleJson:
        """Fetch, enrich, and package Vega records for one connector poll.

        Uses the checkpoint watermark and optional deadline so a long cycle can
        resume without skipping remaining incidents, alerts, or events.
        """
        # 1. Configuration is already on this pipeline (entities, filters, has-related).
        # 2. Time window: first run uses backfill; later runs resume from watermark.
        state = dict(checkpoint or {})
        ingested = list(state.get("ingested_ids") or [])
        ingested_set = set(ingested)
        window = compute_time_window(state, self.backfill_days, self.lookback_minutes)
        records: list[tuple[str, SingleJson]] = []
        plan = self._ingest_plan()

        self._incomplete = False
        self._progress_ts = None
        self._deadline = deadline_monotonic
        self._load_related_backfill(state)

        checkpoint_ids = len(ingested_set)
        self._log(
            "info",
            "Ingest start: entities=%s has_related=%s nest_related=%s "
            "standalone_related=%s standalone_unrelated=%s window=%s checkpoint_ids=%s",
            ",".join(self.entities),
            plan["has_related"],
            plan["nest_related_alerts"],
            plan["standalone_related_alerts"],
            plan["standalone_unrelated_alerts"],
            {key: window.get(key) for key in ("from", "to", "updated_from", "updated_to", "origin_from")},
            checkpoint_ids,
        )

        try:
            if plan["fetch_incidents"]:
                self._ingest_incidents(
                    window,
                    records,
                    ingested,
                    ingested_set,
                    include_related=plan["nest_related_alerts"],
                )
            if not self._should_stop(len(records)) and plan["standalone_related_alerts"]:
                self._ingest_standalone_alerts(window, records, ingested, ingested_set, True, "related")
            if not self._should_stop(len(records)) and plan["standalone_unrelated_alerts"]:
                self._ingest_standalone_alerts(window, records, ingested, ingested_set, False, "unrelated")
        except Exception as exc:
            self._incomplete = True
            self._log(
                "error",
                "Ingest stopped after %s record(s): %s",
                len(records),
                exc,
            )

        if len(ingested) > INGESTED_ID_CAP:
            ingested = ingested[-INGESTED_ID_CAP:]
        state["ingested_ids"] = ingested
        state["origin_from"] = window.get("origin_from") or state.get("origin_from")
        if not self._open_related:
            self._related_scan_offset = 0
            self._related_scan_incomplete = False
        state["related_backfill"] = {
            "offset": self._related_scan_offset,
            "open": self._open_related,
            "settled": self._settled_related,
            "upgrade_ids": list(self._upgrade_incident_ids),
            "batch_version": RELATED_BATCH_VERSION,
            "next_related_batch": self._next_related_batch,
            "related_batch_filled": self._related_batch_filled,
        }
        if self._incomplete:
            # Keep the previous watermark when this cycle packaged nothing.
            if self._progress_ts is not None:
                state["watermark"] = to_iso(self._progress_ts)
            state["incomplete"] = True
            state["query_mode"] = "created"
        else:
            state["watermark"] = window["end"]
            state["incomplete"] = False
            state["query_mode"] = "updated"
        incident_records = sum(1 for kind, _record in records if kind == ENTITY_TYPE_INCIDENT)
        alert_records = sum(1 for kind, _record in records if kind == ENTITY_TYPE_ALERT)
        self._log(
            "info",
            "Step 6 — package ready: %s record(s) will be turned into SecOps "
            "alerts (%s incident, %s alert). Checkpoint already held %s id(s). "
            "incomplete=%s watermark=%s. Nothing in this list was cut to 250.",
            len(records),
            incident_records,
            alert_records,
            checkpoint_ids,
            self._incomplete,
            state.get("watermark"),
        )
        if not records:
            self._log(
                "info",
                "No new Vega records to package. If this connector already ingested "
                "these Vega IDs, reset the connector instance context or wait for new "
                "Vega alerts/incidents.",
            )
        return {
            "records": records,
            "checkpoint": state,
            "fetched": len(records),
            "window": window,
            "incomplete": self._incomplete,
        }
