"""Turn a Vega incident and its related alerts into case records."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson

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
    rank_signals,
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
    def _fetch_alert_metadata_index(self, alert_ids: list[str], window: SingleJson) -> dict[str, SingleJson]:
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

        def _lookup(batch: list[str], *, use_alert_ids: bool) -> list[SingleJson]:
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
                    "warn",
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

    def _vega_alerts_payload(self, incident: SingleJson, window: SingleJson) -> list[SingleJson]:
        """Full getAlerts rows for incident signals (always on)."""
        stubs = incident_alert_stubs(incident)
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

    def _attach_vega_alerts(self, incident: SingleJson, window: SingleJson) -> SingleJson:
        incident = dict(incident)
        incident["vega_alerts"] = self._vega_alerts_payload(incident, window)
        return incident

    def _fetch_alerts_by_ids(self, alert_ids: list[str], window: SingleJson) -> dict[str, SingleJson]:
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

        def _lookup(batch: list[str], *, use_alert_ids: bool) -> list[SingleJson]:
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
                self._log("warn", "Unable to fetch Vega alerts by %s: %s", key, exc)
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
                "warn",
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
                    "warn",
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
                "warn",
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

    def _resolve_related_alerts(self, incident: SingleJson, related_index: dict[str, SingleJson]) -> list[SingleJson]:
        """Match incident.alerts stubs to full getAlerts records (stub if missing)."""
        incident_id = record_id(incident, ENTITY_TYPE_INCIDENT)
        display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
        seen: set[str] = set()
        resolved: list[dict] = []

        def _add(alert: SingleJson) -> None:
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
        alert: SingleJson,
        incident: SingleJson,
        case_tags: list[str | None] = None,
        signal_rank: int = 1,
        total_signals: int = 0,
        signals_in_case: int = 0,
    ) -> SingleJson:
        incident_id = record_id(incident, ENTITY_TYPE_INCIDENT)
        display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
        alert = dict(alert)
        grouping_start, grouping_end = self._incident_time_window(incident)
        incident_link = str(incident.get("link") or incident.get("href") or "").strip()
        incident_summary = str(incident.get("incidentSummary") or "").strip()
        return set_soar_meta(
            alert,
            soar_alert_type=SOAR_ALERT_TYPE_ALERT,
            grouping_id=incident_grouping_id(incident_id),
            case_tags=list(case_tags or []),
            incident_label_tags=record_label_tags(incident),
            case_title=incident_case_title(incident),
            grouping_time=grouping_start or record_timestamp(incident),
            grouping_start=grouping_start,
            grouping_end=grouping_end,
            incident_id=incident_id,
            incident_display_id=display_id,
            incident_name=record_name(incident),
            incident_link=incident_link,
            incident_summary=incident_summary,
            signal_rank=signal_rank,
            total_signals=total_signals,
            signals_in_case=signals_in_case,
            is_incident_case=False,
            is_related_batch=False,
            case_part=0,
        )

    def _append_incident_alert(
        self,
        incident: SingleJson,
        records: list[tuple[str, SingleJson]],
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
        alert: SingleJson,
        incident: SingleJson,
        records: list[tuple[str, SingleJson]],
        ingested: list[str],
        ingested_set: set[str],
        case_tags: list[str | None] = None,
        apply_case_tags: bool = False,
        events_by_id: dict[str, list[SingleJson]] | None = None,
        signal_rank: int = 1,
        total_signals: int = 0,
        signals_in_case: int = 0,
        ingest_key: str | None = None,
    ) -> bool:
        if self._should_stop(len(records)):
            return False
        identifier = record_id(alert, ENTITY_TYPE_ALERT)
        incident_id = record_id(incident, ENTITY_TYPE_INCIDENT)
        # One Vega signal can belong to multiple incidents → unique per case.
        key = ingest_key or (f"{incident_id}:{identifier}" if incident_id else identifier)
        if not identifier or key in ingested_set:
            return False
        try:
            if events_by_id is not None:
                enriched = self._apply_prefetched_events(alert, events_by_id)
            else:
                enriched = self._enrich_alert(alert)
        except Exception as exc:
            self._log(
                "warn",
                "Unable to enrich Vega alert %s; packaging without alert-events: %s",
                identifier,
                exc,
            )
            enriched = dict(alert)
            enriched.setdefault("alert_events", [])
        packaged = self._apply_incident_context(
            enriched,
            incident,
            case_tags=case_tags,
            signal_rank=signal_rank,
            total_signals=total_signals,
            signals_in_case=signals_in_case,
        )
        if apply_case_tags:
            packaged = set_soar_meta(packaged, apply_case_tags=True)
        records.append((ENTITY_TYPE_ALERT, packaged))
        self._mark_ingested(ingested, ingested_set, key)
        self._note_progress(packaged)
        return True

    def _ordered_stubs(self, incident: SingleJson) -> list[SingleJson]:
        return self._sort_by_timestamp(incident_alert_stubs(incident))

    def _pending_stubs(self, incident: SingleJson, ingested_set: set[str]) -> list[SingleJson]:
        pending: list[dict] = []
        for stub in self._ordered_stubs(incident):
            keys = record_alert_ids(stub)
            if not keys or any(key in ingested_set for key in keys):
                continue
            pending.append(stub)
        return pending

    def _stub_lookup_ids(self, stubs: list[SingleJson]) -> list[str]:
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
        incident: SingleJson,
        related: list[SingleJson],
        records: list[tuple[str, SingleJson]],
        ingested: list[str],
        ingested_set: set[str],
    ) -> None:
        """Emit top-N signal AlertInfos for one incident (one SecOps case).

        No synthetic incident alert. Overflow signals stay in Vega; SyncAlerts
        writes ``"{total} signals, {N} in case"`` into case insight.
        """
        identifier = record_id(incident, ENTITY_TYPE_INCIDENT)
        display_id = record_display_id(incident, ENTITY_TYPE_INCIDENT)
        label = (
            f"{display_id} ({identifier})" if display_id and display_id != identifier else (identifier or display_id)
        )
        resolved_index: dict[str, dict] = {}
        for alert in related or []:
            if not isinstance(alert, dict):
                continue
            for key in record_alert_ids(alert):
                resolved_index.setdefault(key, alert)
        queue: list[dict] = []
        known: set[str] = set()
        for stub in incident_alert_stubs(incident):
            keys = record_alert_ids(stub)
            if not keys:
                continue
            ingest_key = f"{identifier}:{keys[0]}" if identifier else keys[0]
            if ingest_key in ingested_set or any(key in ingested_set for key in keys):
                continue
            if any(key in known for key in keys):
                continue
            known.update(keys)
            full = None
            for key in keys:
                full = resolved_index.get(key)
                if full:
                    break
            queue.append(full or stub)
        for alert in related or []:
            keys = record_alert_ids(alert)
            if not keys:
                continue
            ingest_key = f"{identifier}:{keys[0]}" if identifier else keys[0]
            if ingest_key in ingested_set or any(key in known or key in ingested_set for key in keys):
                continue
            known.update(keys)
            queue.append(alert)
        total_signals = 0
        try:
            total_signals = max(int(incident.get("alertsCount") or 0), len(queue))
        except (TypeError, ValueError):
            total_signals = len(queue)
        if not queue:
            self._log(
                "info",
                "Vega incident %s: no signals to package (total_signals=%s).",
                label,
                total_signals,
            )
            # Mark incident visited so we do not re-enrich forever.
            if identifier:
                self._mark_ingested(ingested, ingested_set, f"incident:{identifier}")
            return
        case_size = max(1, int(getattr(self, "max_alerts_in_case", 30)))
        selected = rank_signals(queue, case_size)
        signals_in_case = len(selected)
        self._log(
            "info",
            "Step 6 — %s: %s signal(s) total, packaging top %s "
            "(Max Alerts in Case=%s). Ranking: ESCALATED, severity, oldest.",
            label,
            total_signals,
            signals_in_case,
            case_size,
        )
        case_tags = collect_label_tags(incident, *selected)
        event_batch = max(1, int(ALERT_EVENTS_ID_BATCH))
        packaged = 0
        offset = 0
        stopped_early = False
        while offset < len(selected):
            if self._should_stop(len(records)):
                stopped_early = True
                break
            window = selected[offset : offset + event_batch]
            pending = list(window)
            remaining = self._remaining(len(records))
            if remaining is not None:
                pending = pending[:remaining]
            events_by_id = self._fetch_events_for_alerts(pending) if pending else {}
            halt = False
            for batch_index, alert in enumerate(window):
                rank = offset + batch_index + 1
                alert_id = record_id(alert, ENTITY_TYPE_ALERT)
                ingest_key = f"{identifier}:{alert_id}" if identifier and alert_id else alert_id
                if self._append_related_alert(
                    alert,
                    incident,
                    records,
                    ingested,
                    ingested_set,
                    case_tags=case_tags,
                    apply_case_tags=rank == 1,
                    events_by_id=events_by_id,
                    signal_rank=rank,
                    total_signals=total_signals,
                    signals_in_case=signals_in_case,
                    ingest_key=ingest_key,
                ):
                    packaged += 1
                elif self._should_stop(len(records)):
                    stopped_early = True
                    halt = True
                    break
            if halt:
                break
            offset += event_batch
        overflow = max(total_signals - packaged, 0)
        self._log(
            "info",
            "Step 6 — %s: added %s signal alert(s)%s.",
            label,
            packaged,
            (
                f"; {overflow} past the cap stay in Vega only"
                if overflow and not stopped_early
                else (
                    f"; stopped early with {max(signals_in_case - packaged, 0)} still waiting"
                    if stopped_early
                    else ""
                )
            ),
        )
        if identifier and not stopped_early:
            self._mark_ingested(ingested, ingested_set, f"incident:{identifier}")
