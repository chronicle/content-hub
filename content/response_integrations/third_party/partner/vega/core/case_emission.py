"""Turn a Vega incident and its related alerts into case records."""

from __future__ import annotations

import time

from .constants import (
    ALERT_EVENTS_ID_BATCH,
    ALERT_ID_LOOKUP_BATCH,
    ALERT_METADATA_ID_BATCH,
    ENTITY_TYPE_ALERT,
    ENTITY_TYPE_INCIDENT,
    SOAR_ALERT_TYPE_ALERT,
    SOAR_ALERT_TYPE_INCIDENT,
)
from .mapping import (
    collect_label_tags,
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


class CaseEmissionMixin:
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
        from .IngestionPipeline import MAX_ALERTS_PER_CASE

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
        from .IngestionPipeline import MAX_ALERTS_PER_CASE

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
