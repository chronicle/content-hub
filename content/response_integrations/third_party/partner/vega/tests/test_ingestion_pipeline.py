"""Tests for incident → top-N signal packaging (one case, never splits)."""

from __future__ import annotations

from core.constants import ENTITY_TYPE_ALERT
from core.IngestionPipeline import IngestionPipeline
from core.mapping import soar_meta


class FakeManager:
    def __init__(self) -> None:
        self.incidents: list[dict] = []
        self.alerts: list[dict] = []
        self.alert_events: dict[str, list] = {}
        self.timelines: dict[str, list] = {}
        self.alert_calls: list[dict] = []
        self.event_batch_calls: list[list[str]] = []
        self.timeline_calls: list[str] = []
        self.last_fetch_truncated = False

    def get_incidents(self, variables, max_records=None, deadline_monotonic=None, **_kwargs):
        rows = list(self.incidents)
        if max_records is not None:
            return rows[:max_records]
        return rows

    def get_alerts(
        self,
        variables,
        max_records=None,
        deadline_monotonic=None,
        start_offset=0,
        **_kwargs,
    ):
        variables = dict(variables or {})
        self.alert_calls.append(variables)
        alert_ids = {str(item) for item in (variables.get("alertIds") or []) if item}
        vega_ids = {str(item) for item in (variables.get("vegaAlertIds") or []) if item}
        lookup_ids = alert_ids | vega_ids
        rows = []
        for alert in self.alerts:
            keys = {
                str(alert.get("id") or ""),
                str(alert.get("vegaAlertId") or ""),
                str(alert.get("alertId") or ""),
            }
            keys.discard("")
            if lookup_ids and not keys.intersection(lookup_ids):
                continue
            rows.append(alert)
        offset = max(int(start_offset or 0), 0)
        if max_records is not None:
            return rows[offset : offset + int(max_records)]
        return rows[offset:]

    def count_alerts(self, variables):
        return len(self.get_alerts(variables))

    def get_all_alert_events(self, alert_id, page_size=None, max_records=None, deadline_monotonic=None, **_kwargs):
        return list(self.alert_events.get(alert_id) or [])

    def get_all_alerts_events(
        self,
        alert_ids,
        page_size=None,
        max_records=None,
        deadline_monotonic=None,
        **_kwargs,
    ):
        ids = [str(item) for item in (alert_ids or []) if str(item or "").strip()]
        self.event_batch_calls.append(ids)
        return {alert_id: list(self.alert_events.get(alert_id) or []) for alert_id in ids}

    def get_all_incident_timeline(self, incident_id, page_size=None, deadline_monotonic=None, **_kwargs):
        self.timeline_calls.append(incident_id)
        return list(self.timelines.get(incident_id) or [])


def _pipeline(
    manager: FakeManager,
    max_alerts_in_case: int = 30,
    max_fetch: int = 50,
    **filter_kwargs,
) -> IngestionPipeline:
    return IngestionPipeline(
        manager=manager,
        lookback_minutes="5",
        backfill_days="0",
        max_alerts_in_case=max_alerts_in_case,
        max_fetch=max_fetch,
        **filter_kwargs,
    )


def _sample_manager() -> FakeManager:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "alertsCount": 3,
            "labels": [{"name": "malware"}],
            "alerts": [
                {"alertId": "alert-1", "name": "Phish"},
                {"alertId": "alert-2", "name": "Beacon"},
                {"alertId": "alert-3", "name": "Noise"},
            ],
        }
    ]
    manager.alerts = [
        {
            "id": "alert-1",
            "vegaAlertId": "VALERT-1",
            "name": "Phish",
            "severity": "HIGH",
            "createdAt": "2026-02-01T00:00:00Z",
            "escalation": {"status": "ESCALATED"},
            "relatedIncidents": [{"incidentId": "inc-1"}],
            "labels": [{"name": "phish"}],
        },
        {
            "id": "alert-2",
            "vegaAlertId": "VALERT-2",
            "name": "Beacon",
            "severity": "CRITICAL",
            "createdAt": "2026-03-01T00:00:00Z",
            "escalation": {"status": "NOT_ESCALATED"},
            "relatedIncidents": [{"incidentId": "inc-1"}],
            "labels": [{"name": "beacon"}],
        },
        {
            "id": "alert-3",
            "vegaAlertId": "VALERT-3",
            "name": "Noise",
            "severity": "LOW",
            "createdAt": "2026-01-01T00:00:00Z",
            "escalation": {"status": "SKIPPED"},
            "relatedIncidents": [{"incidentId": "inc-1"}],
        },
        {
            "id": "alert-99",
            "vegaAlertId": "VALERT-99",
            "name": "Unrelated",
            "relatedIncidents": [],
        },
    ]
    manager.alert_events = {"alert-1": [{"name": "login"}]}
    return manager


def test_emits_signals_only_same_grouping_id() -> None:
    manager = _sample_manager()
    result = _pipeline(manager).run()
    records = result["records"]
    assert all(kind == ENTITY_TYPE_ALERT for kind, _ in records)
    assert len(records) == 3
    grouping = {soar_meta(record)["grouping_id"] for _, record in records}
    assert grouping == {"Vega:incident:inc-1"}
    ranks = [soar_meta(record)["signal_rank"] for _, record in records]
    assert ranks == [1, 2, 3]
    assert soar_meta(records[0][1])["signal_rank"] == 1
    assert records[0][1]["id"] == "alert-1"  # ESCALATED first


def test_max_alerts_in_case_caps_and_sets_overflow_meta() -> None:
    manager = _sample_manager()
    result = _pipeline(manager, max_alerts_in_case=2).run()
    records = result["records"]
    assert len(records) == 2
    meta = soar_meta(records[0][1])
    assert meta["total_signals"] == 3
    assert meta["signals_in_case"] == 2
    assert [record["id"] for _, record in records] == ["alert-1", "alert-2"]


def test_alert_filters_hard_drop_related_signals() -> None:
    manager = _sample_manager()
    for alert in manager.alerts:
        if alert["id"] == "alert-1":
            alert["status"] = "OPEN"
        elif alert["id"] == "alert-2":
            alert["status"] = "RESOLVED"
        elif alert["id"] == "alert-3":
            alert["status"] = "OPEN"
    result = _pipeline(
        manager,
        alert_severities="HIGH,CRITICAL",
        alert_statuses="OPEN",
    ).run()
    records = result["records"]
    assert [record["id"] for _, record in records] == ["alert-1"]
    assert soar_meta(records[0][1])["total_signals"] == 3


def test_does_not_fetch_unrelated_alerts() -> None:
    manager = _sample_manager()
    result = _pipeline(manager).run()
    ids = {record["id"] for _, record in result["records"]}
    assert "alert-99" not in ids
    # Lookups are by alertIds from the incident, never hasRelatedIncidents=false sweep.
    for call in manager.alert_calls:
        assert call.get("hasRelatedIncidents") is not False or call.get("alertIds") or call.get("vegaAlertIds")


def test_multi_incident_signal_gets_per_incident_ingest_key() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-a",
            "name": "A",
            "alertsCount": 1,
            "alerts": [{"alertId": "shared"}],
        },
        {
            "id": "inc-b",
            "name": "B",
            "alertsCount": 1,
            "alerts": [{"alertId": "shared"}],
        },
    ]
    manager.alerts = [
        {
            "id": "shared",
            "name": "Shared",
            "severity": "HIGH",
            "createdAt": "2026-01-01T00:00:00Z",
            "escalation": {"status": "ESCALATED"},
            "relatedIncidents": [{"incidentId": "inc-a"}, {"incidentId": "inc-b"}],
        }
    ]
    result = _pipeline(manager).run()
    records = result["records"]
    assert len(records) == 2
    groups = sorted(soar_meta(record)["grouping_id"] for _, record in records)
    assert groups == ["Vega:incident:inc-a", "Vega:incident:inc-b"]


def test_preview_returns_signal_samples() -> None:
    manager = _sample_manager()
    preview = _pipeline(manager).preview(sample_limit=2)
    assert preview["incident_count"] == 1
    assert preview["related_alert_count"] == 3
    assert preview["include_unrelated"] is False
    assert len(preview["records"]) == 2
    assert all(kind == ENTITY_TYPE_ALERT for kind, _ in preview["records"])


def test_checkpoint_skips_already_packaged_incident() -> None:
    manager = _sample_manager()
    pipeline = _pipeline(manager)
    first = pipeline.run()
    assert first["records"]
    second = pipeline.run(checkpoint=first["checkpoint"])
    assert second["records"] == []
