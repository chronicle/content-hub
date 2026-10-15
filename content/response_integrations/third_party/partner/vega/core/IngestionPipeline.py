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

logger = logging.getLogger(__name__)


def _drop_none(payload: dict) -> dict:
    return {key: value for key, value in payload.items() if value is not None}


class IngestionPipeline:
    """Poll Vega and return packages that match SecOps Case > Alert > Event."""

    def __init__(
        self,
        manager,
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
        logger_instance=None,
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
        self._incident_cache: dict[str, dict] = {}
        self._incomplete = False
        self._progress_ts: datetime | None = None
        self._deadline: float | None = None
        self._open_related: dict[str, dict] = {}
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
        window: dict,
        has_related: bool | None,
        alert_ids: list[str | None] = None,
        vega_alert_ids: list[str | None] = None,
        include_time: bool = True,
    ) -> dict:
        payload: dict = {}
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

    def _incident_variables(self, window: dict) -> dict:
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

    def _enrich_incident(self, record: dict) -> dict:
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

    def _note_progress(self, record: dict) -> None:
        parsed = parse_iso_timestamp(record_timestamp(record))
        if parsed is None:
            return
        if self._progress_ts is None or parsed > self._progress_ts:
            self._progress_ts = parsed

    def _sort_by_timestamp(self, rows: list[dict]) -> list[dict]:
        return sorted(rows, key=lambda row: record_timestamp(row) or "")

    def _preferred_event_id(self, record: dict) -> str:
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

    def _apply_prefetched_events(self, record: dict, events_by_id: dict[str, list]) -> dict:
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

    def _fetch_events_for_alerts(self, alerts: list[dict]) -> dict[str, list]:
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

    def _fetch_events_one_by_one(self, alerts: list[dict]) -> dict[str, list]:
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

    def _enrich_alert(self, record: dict) -> dict:
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

    def _cache_incident(self, incident: dict) -> None:
        identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
        if identifier:
            self._incident_cache[identifier] = incident
        display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
        if display_id:
            self._incident_cache[display_id] = incident

    def _id_lookup_window(self, window: dict) -> dict:
        """Wide created/updated range so related alerts older than the ingest window still resolve."""
        end = (window or {}).get("to") or (window or {}).get("updated_to") or (window or {}).get("end")
        return {
            "from": ALERT_ID_LOOKUP_FROM,
            "to": end,
            "updated_from": ALERT_ID_LOOKUP_FROM,
            "updated_to": end,
        }

    def _metadata_lookup_ids(self, incident: dict) -> list[str]:
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

    def _fetch_alert_metadata_index(self, alert_ids: list[str], window: dict) -> dict[str, dict]:
        """Load full getAlerts rows for incident alert ids.

        UUID ids go in alertIds, at most 1000 per request. getAlerts pages
        the response with limit/offset until that batch is collected. Human
        ids use vegaAlertIds so a non-UUID cannot fail the UUID batch.
        """
        graphql_ids = [item for item in alert_ids if is_graphql_alert_id(item)]
        other_ids = [item for item in alert_ids if item not in graphql_ids]
        if not graphql_ids and not other_ids:
            return {}
        collected: list[dict] = []
        batch_size = max(1, int(ALERT_METADATA_ID_BATCH))
        lookup_window = self._id_lookup_window(window)

        def _lookup(batch: list[str], *, use_alert_ids: bool) -> list[dict]:
            key = "alertIds" if use_alert_ids else "vegaAlertIds"
            try:
                if use_alert_ids:
                    variables = self._alert_variables(lookup_window, None, alert_ids=batch)
                else:
                    variables = self._alert_variables(lookup_window, None, vega_alert_ids=batch)
                page = self.manager.get_alerts(
                    variables,
                    len(batch),
                    deadline_monotonic=self._deadline,
                    page_size=len(batch),
                )
                self._mark_if_truncated()
            except Exception as exc:
                self._log(
                    "warning",
                    "Unable to fetch related-alert metadata by %s: %s",
                    key,
                    exc,
                )
                return []
            return [item for item in page if isinstance(item, dict)]

        def _lookup_batches(ids: list[str], *, use_alert_ids: bool) -> None:
            for index in range(0, len(ids), batch_size):
                if self._deadline_reached():
                    self._incomplete = True
                    return
                collected.extend(
                    _lookup(
                        ids[index : index + batch_size],
                        use_alert_ids=use_alert_ids,
                    )
                )

        _lookup_batches(graphql_ids, use_alert_ids=True)
        _lookup_batches(other_ids, use_alert_ids=False)
        self._log(
            "info",
            "Fetched %s related-alert metadata record(s) for %s alert id(s).",
            len(collected),
            len(alert_ids),
        )
        return index_alert_records(collected)

    def _vega_alerts_payload(self, incident: dict, window: dict) -> list[dict]:
        """Related alerts for the incident vega_alerts property.

        Checkbox off: getIncidents stubs (alertId, name, createdAt).
        Checkbox on: full getAlerts records, stub when an id is missing.
        """
        stubs = incident_alert_stubs(incident)
        if not self.fetch_related_alert_metadata:
            payload: list[dict] = []
            for stub in stubs:
                summary = incident_alert_summary(stub)
                if summary:
                    payload.append(summary)
            return payload
        lookup_ids = self._metadata_lookup_ids(incident)
        index = self._fetch_alert_metadata_index(lookup_ids, window) if lookup_ids else {}
        payload: list[dict] = []
        for stub in stubs:
            full = None
            for key in record_alert_ids(stub):
                match = index.get(key)
                if isinstance(match, dict):
                    full = match
                    break
            if full is not None:
                payload.append(dict(full))
                continue
            summary = incident_alert_summary(stub)
            if summary:
                payload.append(summary)
        return payload

    def _attach_vega_alerts(self, incident: dict, window: dict) -> dict:
        incident = dict(incident)
        incident["vega_alerts"] = self._vega_alerts_payload(incident, window)
        return incident

    def _fetch_alerts_by_ids(self, alert_ids: list[str], window: dict) -> dict[str, dict]:
        """Resolve full alert records (including labels) for incident alertIds.

        Vega getAlerts often returns 0 rows for alertIds without a time bound,
        so ID lookups use a wide createdAt window rather than the ingest window.
        Related alerts are often months older than the incident update.

        Do not send human vegaAlertIds (VEGA-123) in alertIds: [ID!]. That can
        fail the whole batch and leave stubs with empty labels.
        """
        unique: list[str] = []
        seen: set[str] = set()
        for alert_id in alert_ids:
            value = str(alert_id or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            unique.append(value)
        if not unique:
            return {}
        graphql_ids = [item for item in unique if is_graphql_alert_id(item)]
        vega_ids = [item for item in unique if item not in graphql_ids]
        collected: list[dict] = []
        batch_size = max(1, int(ALERT_ID_LOOKUP_BATCH))
        lookup_window = self._id_lookup_window(window)

        def _lookup(batch: list[str], *, use_alert_ids: bool) -> list[dict]:
            key = "alertIds" if use_alert_ids else "vegaAlertIds"
            try:
                if use_alert_ids:
                    variables = self._alert_variables(lookup_window, None, alert_ids=batch)
                else:
                    variables = self._alert_variables(lookup_window, None, vega_alert_ids=batch)
                page = self.manager.get_alerts(
                    variables,
                    len(batch),
                    deadline_monotonic=self._deadline,
                    page_size=len(batch),
                )
                self._mark_if_truncated()
            except Exception as exc:
                self._log("warning", "Unable to fetch Vega alerts by %s: %s", key, exc)
                return []
            return [item for item in page if isinstance(item, dict)]

        def _lookup_batches(ids: list[str], *, use_alert_ids: bool) -> None:
            total_batches = (len(ids) + batch_size - 1) // batch_size if ids else 0
            key_name = "alertIds" if use_alert_ids else "vegaAlertIds"
            for batch_number, index in enumerate(range(0, len(ids), batch_size), start=1):
                if self._deadline_reached():
                    self._incomplete = True
                    self._log(
                        "info",
                        "Step 4 — stopped before getAlerts batch %s of %s "
                        "(%s). The connector time limit was reached, so %s "
                        "id(s) were not requested this run.",
                        batch_number,
                        total_batches,
                        key_name,
                        len(ids) - index,
                    )
                    return
                batch = ids[index : index + batch_size]
                returned = _lookup(batch, use_alert_ids=use_alert_ids)
                collected.extend(returned)
                self._log(
                    "info",
                    "Step 4 — getAlerts batch %s of %s (%s): sent %s id(s) with limit %s, received %s alert record(s).",
                    batch_number,
                    total_batches,
                    key_name,
                    len(batch),
                    len(batch),
                    len(returned),
                )

        def _found_ids() -> set[str]:
            found: set[str] = set()
            for alert in collected:
                found.update(record_alert_ids(alert))
            return found

        def _retry_missing(ids: list[str], *, use_alert_ids: bool) -> None:
            """A batched getAlerts call can omit ids. Call each missing id."""
            found = _found_ids()
            missing = [item for item in ids if item not in found]
            for alert_id in missing:
                if self._deadline_reached():
                    self._incomplete = True
                    return
                collected.extend(_lookup([alert_id], use_alert_ids=use_alert_ids))

        _lookup_batches(graphql_ids, use_alert_ids=True)
        _retry_missing(graphql_ids, use_alert_ids=True)
        pending_vega = [item for item in vega_ids if item not in _found_ids()]
        if pending_vega:
            _lookup_batches(pending_vega, use_alert_ids=False)
            _retry_missing(pending_vega, use_alert_ids=False)

        if not collected:
            self._log(
                "warning",
                "getAlerts(alertIds) returned 0 of %s ids; falling back to "
                "hasRelatedIncidents=true in the ingest window.",
                len(unique),
            )
            try:
                collected = [
                    item
                    for item in self.manager.get_alerts(
                        self._alert_variables(window, True),
                        self._pool_limit(),
                        deadline_monotonic=self._deadline,
                    )
                    if isinstance(item, dict)
                ]
                self._mark_if_truncated()
            except Exception as exc:
                self._log(
                    "warning",
                    "Fallback getAlerts(hasRelatedIncidents=true) failed: %s",
                    exc,
                )
                collected = []
        found = _found_ids()
        missing = [item for item in unique if item not in found]
        self._log(
            "info",
            "Step 4 — getAlerts finished: requested %s id(s), received %s "
            "alert record(s), matched %s of those ids, %s id(s) still missing.",
            len(unique),
            len(collected),
            len(unique) - len(missing),
            len(missing),
        )
        if missing:
            sample = ", ".join(missing[:10])
            extra = "" if len(missing) <= 10 else f" and {len(missing) - 10} more"
            self._log(
                "warning",
                "Step 4 — getAlerts did not return these ids: %s%s. "
                "They are still packaged from the nested incident stub.",
                sample,
                extra,
            )
        return index_alert_records(collected)

    def _pool_limit(self) -> int | None:
        if self.max_fetch is None:
            return None
        return max(self.max_fetch * 10, self.max_fetch)

    def _resolve_related_alerts(self, incident: dict, related_index: dict[str, dict]) -> list[dict]:
        """Match incident.alerts stubs to full getAlerts records (stub if missing)."""
        incident_id = record_id(incident, ENTITY_TYPE_INCIDENT)
        display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
        seen: set[str] = set()
        resolved: list[dict] = []

        def _add(alert: dict) -> None:
            identifier = record_id(alert, ENTITY_TYPE_ALERT)
            if not identifier or identifier in seen:
                return
            seen.add(identifier)
            resolved.append(alert)

        full_matches = 0
        stub_only = 0
        for stub in incident_alert_stubs(incident):
            full = None
            for key in record_alert_ids(stub):
                full = related_index.get(key)
                if full:
                    break
            if full:
                full_matches += 1
            else:
                stub_only += 1
            _add(merge_related_alert(stub, full))
        from_stubs = len(resolved)

        wanted = {incident_id, display_id}
        wanted.discard("")
        for alert in related_index.values():
            if wanted.intersection(related_incident_ids(alert)):
                _add(alert)
        label = (
            f"{display_id} ({incident_id})" if display_id and display_id != incident_id else (incident_id or display_id)
        )
        self._log(
            "info",
            "Step 5 — %s: nested stubs=%s, full getAlerts records=%s, "
            "stub only=%s, extra alerts matched by incident id=%s, "
            "total that will be packaged=%s.",
            label,
            full_matches + stub_only,
            full_matches,
            stub_only,
            len(resolved) - from_stubs,
            len(resolved),
        )
        return resolved

    def _apply_incident_context(
        self,
        alert: dict,
        incident: dict,
        case_tags: list[str | None] = None,
        batch: int = 1,
    ) -> dict:
        incident_id = record_id(incident, ENTITY_TYPE_INCIDENT)
        display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
        alert = dict(alert)
        # Related alerts keep their own Vega labels. Empty stays empty on the
        # event (`[]`); never copy incident labels onto a related alert's
        # `labels` field. Incident names still go on case_tags and
        # incident_label_tags so the related-alert case can tag from events.
        if incident.get("timeline") and not alert.get("timeline"):
            alert["timeline"] = incident.get("timeline")
        description = str(alert.get("description") or "").strip()
        summary = str(
            incident.get("incidentSummary") or incident.get("incidentFindings") or incident.get("description") or ""
        ).strip()
        if summary and summary not in description:
            alert["description"] = f"{summary}\n\n{description}".strip() if description else summary
        grouping_start, grouping_end = self._incident_time_window(incident)
        return set_soar_meta(
            alert,
            soar_alert_type=SOAR_ALERT_TYPE_ALERT,
            grouping_id=incident_grouping_id(incident_id, related=True, batch=batch),
            case_tags=list(case_tags or []),
            incident_label_tags=record_label_tags(incident),
            case_title=incident_case_title(incident, batch=batch),
            grouping_time=grouping_start or record_timestamp(incident),
            grouping_start=grouping_start,
            grouping_end=grouping_end,
            incident_id=incident_id,
            incident_display_id=display_id,
            incident_name=record_name(incident),
            is_incident_case=True,
            is_related_batch=True,
            case_part=batch,
        )

    def _append_incident_alert(
        self,
        incident: dict,
        records: list[tuple[str, dict]],
        ingested: list[str],
        ingested_set: set[str],
        case_tags: list[str | None] = None,
    ) -> bool:
        if self._should_stop(len(records)):
            return False
        identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
        synthetic_key = f"incident:{identifier}"
        if not identifier or synthetic_key in ingested_set:
            return False
        display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
        packaged = set_soar_meta(
            incident,
            soar_alert_type=SOAR_ALERT_TYPE_INCIDENT,
            grouping_id=incident_grouping_id(identifier),
            case_tags=list(case_tags or []),
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
        self._mark_ingested(ingested, ingested_set, synthetic_key)
        self._note_progress(packaged)
        return True

    def _append_related_alert(
        self,
        alert: dict,
        incident: dict,
        records: list[tuple[str, dict]],
        ingested: list[str],
        ingested_set: set[str],
        case_tags: list[str | None] = None,
        apply_case_tags: bool = False,
        events_by_id: dict[str, list | None] = None,
        batch: int | None = None,
    ) -> bool:
        if self._should_stop(len(records)):
            return False
        identifier = record_id(alert, ENTITY_TYPE_ALERT)
        if not identifier or identifier in ingested_set:
            return False
        incident_id = record_id(incident, ENTITY_TYPE_INCIDENT)
        if batch is None:
            batch = self._consume_related_batch_slot(incident_id)
        try:
            if events_by_id is not None:
                enriched = self._apply_prefetched_events(alert, events_by_id)
            else:
                enriched = self._enrich_alert(alert)
        except Exception as exc:
            self._log(
                "warning",
                "Unable to enrich Vega alert %s; packaging without events: %s",
                identifier,
                exc,
            )
            enriched = dict(alert)
            enriched.setdefault("alert_events", [])
        packaged = self._apply_incident_context(enriched, incident, case_tags=case_tags, batch=batch)
        if apply_case_tags:
            packaged = set_soar_meta(packaged, apply_case_tags=True)
        records.append((ENTITY_TYPE_ALERT, packaged))
        self._mark_ingested(ingested, ingested_set, identifier)
        self._note_progress(packaged)
        return True

    def _ordered_stubs(self, incident: dict) -> list[dict]:
        return self._sort_by_timestamp(incident_alert_stubs(incident))

    def _pending_stubs(self, incident: dict, ingested_set: set[str]) -> list[dict]:
        pending: list[dict] = []
        for stub in self._ordered_stubs(incident):
            keys = record_alert_ids(stub)
            if not keys or any(key in ingested_set for key in keys):
                continue
            pending.append(stub)
        return pending

    def _stub_lookup_ids(self, stubs: list[dict]) -> list[str]:
        ids: list[str] = []
        seen: set[str] = set()
        for stub in stubs:
            for key in record_alert_ids(stub):
                if key not in seen:
                    seen.add(key)
                    ids.append(key)
        return ids

    def _consume_related_batch_slot(self, incident_id: str) -> int:
        """Assign the next monotonic batch number for a related alert (max 90 per batch)."""
        if not incident_id:
            return 1
        case_size = max(1, int(MAX_ALERTS_PER_CASE))
        try:
            batch_no = max(int(self._next_related_batch.get(incident_id, 1)), 1)
        except (TypeError, ValueError):
            batch_no = 1
        try:
            filled = max(int(self._related_batch_filled.get(incident_id, 0)), 0)
        except (TypeError, ValueError):
            filled = 0
        if filled >= case_size:
            batch_no += 1
            filled = 0
        self._next_related_batch[incident_id] = batch_no
        self._related_batch_filled[incident_id] = filled + 1
        return batch_no

    def _emit_incident_cases(
        self,
        incident: dict,
        related: list[dict],
        records: list[tuple[str, dict]],
        ingested: list[str],
        ingested_set: set[str],
    ) -> None:
        """Incident case, then every related alert.

        Batch numbers and ``Vega:incident:<id>:related:batch:<N>`` grouping
        keys advance in ingest order (up to 90 alerts per batch) and persist
        in the checkpoint so batch numbers are not reused across runs.
        """
        identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
        display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
        label = (
            f"{display_id} ({identifier})" if display_id and display_id != identifier else (identifier or display_id)
        )
        self._append_incident_alert(
            incident,
            records,
            ingested,
            ingested_set,
            case_tags=collect_label_tags(incident),
        )
        if not related:
            return
        ordered = self._ordered_stubs(incident)
        case_size = max(1, int(MAX_ALERTS_PER_CASE))
        resolved_index: dict[str, dict] = {}
        for alert in related or []:
            if not isinstance(alert, dict):
                continue
            for key in record_alert_ids(alert):
                resolved_index.setdefault(key, alert)
        queue: list[dict] = []
        known: set[str] = set()
        for stub in self._pending_stubs(incident, ingested_set):
            keys = record_alert_ids(stub)
            known.update(keys)
            full = None
            for key in keys:
                full = resolved_index.get(key)
                if full:
                    break
            queue.append(full or stub)
        for alert in related or []:
            keys = record_alert_ids(alert)
            if not keys or any(key in known or key in ingested_set for key in keys):
                continue
            known.update(keys)
            queue.append(alert)
        if not ordered and not queue:
            self._log(
                "info",
                "Vega incident %s: no related alert ids were loaded, so no related-alert cases will be created.",
                label,
            )
            return
        already_sent = max(len(ordered) - len(self._pending_stubs(incident, ingested_set)), 0)
        to_package = len(queue)
        try:
            next_batch = max(int(self._next_related_batch.get(identifier, 1)), 1)
        except (TypeError, ValueError):
            next_batch = 1
        self._log(
            "info",
            "Step 6 — %s: %s related alert(s) in batches of %s. "
            "%s already checkpointed. This run adds all %s "
            "(starting at batch %s). Each batch uses its own source grouping "
            "identifier.",
            label,
            len(ordered) or to_package,
            case_size,
            already_sent,
            to_package,
            next_batch,
        )
        if not queue:
            return
        case_tags = collect_label_tags(incident, *queue)
        event_batch = max(1, int(ALERT_EVENTS_ID_BATCH))
        offset = 0
        stopped_early = False
        packaged = 0
        while offset < len(queue):
            if self._should_stop(len(records)):
                stopped_early = True
                break
            window = queue[offset : offset + event_batch]
            pending = list(window)
            remaining = self._remaining(len(records))
            if remaining is not None:
                pending = pending[:remaining]
            events_by_id = self._fetch_events_for_alerts(pending) if pending else {}
            halt = False
            for batch_index, alert in enumerate(window):
                if self._append_related_alert(
                    alert,
                    incident,
                    records,
                    ingested,
                    ingested_set,
                    case_tags=case_tags,
                    apply_case_tags=(offset + batch_index) == 0,
                    events_by_id=events_by_id,
                ):
                    packaged += 1
                elif self._should_stop(len(records)):
                    stopped_early = True
                    halt = True
                    break
            if halt:
                break
            offset += event_batch
        still_waiting = max(to_package - packaged, 0)
        if still_waiting and stopped_early:
            self._log(
                "info",
                "Step 6 — %s: added %s related alert(s) to this package. "
                "%s are still waiting because the connector time limit was "
                "reached. The next run will fetch and package those.",
                label,
                packaged,
                still_waiting,
            )
        elif still_waiting:
            self._log(
                "warning",
                "Step 6 — %s: added %s related alert(s) to this package. %s were not packaged.",
                label,
                packaged,
                still_waiting,
            )
        else:
            self._log(
                "info",
                "Step 6 — %s: added %s related alert(s) to this package. "
                "None are left waiting in the connector. SecOps has not "
                "created the cases yet.",
                label,
                packaged,
            )

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

    def _ingest_incidents(
        self,
        window: dict,
        records: list[tuple[str, dict]],
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
        related_index: dict[str, dict] = {}
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
        alert: dict,
        records: list[tuple[str, dict]],
        ingested: list[str],
        ingested_set: set[str],
        events_by_id: dict[str, list | None] = None,
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
        window: dict,
        records: list[tuple[str, dict]],
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

    def _ingest_plan(self) -> dict:
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
        window: dict,
        records: list[tuple[str, dict]],
        remaining: int,
        incidents: list[dict | None] = None,
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
        window: dict,
        records: list[tuple[str, dict]],
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

    def _related_alert_count(self, incidents: list[dict]) -> int:
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

    def preview(self, sample_limit: int = TEST_RUN_MAX_FETCH) -> dict:
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
        incidents: list[dict] = []
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
        records: list[tuple[str, dict]] = []
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
        checkpoint: dict | None = None,
        deadline_monotonic: float | None = None,
    ) -> dict:
        # 1. Configuration is already on this pipeline (entities, filters, has-related).
        # 2. Time window: first run uses backfill; later runs resume from watermark.
        state = dict(checkpoint or {})
        ingested = list(state.get("ingested_ids") or [])
        ingested_set = set(ingested)
        window = compute_time_window(state, self.backfill_days, self.lookback_minutes)
        records: list[tuple[str, dict]] = []
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
