"""Tests for incident-case vs unrelated-alert ingestion."""

from __future__ import annotations

import time

from core.constants import (
    ENTITY_TYPE_ALERT,
    ENTITY_TYPE_INCIDENT,
    SOAR_ALERT_TYPE_ALERT,
    SOAR_ALERT_TYPE_INCIDENT,
)
from core.IngestionPipeline import IngestionPipeline
from core.mapping import soar_meta


class FakeManager:
    def __init__(self) -> None:
        self.incidents: list[dict] = []
        self.alerts: list[dict] = []
        self.alert_events: dict[str, list] = {}
        self.timelines: dict[str, list] = {}
        self.incident_by_id: dict[str, dict] = {}
        self.alert_calls: list[dict] = []
        self.alert_fetch_limits: list = []
        self.incident_calls: list[dict] = []
        self.event_calls: list[str] = []
        self.event_batch_calls: list[list[str]] = []
        self.timeline_calls: list[str] = []
        self.last_fetch_truncated = False

    def get_incidents(self, variables, max_records=None, deadline_monotonic=None, **_kwargs):
        self.incident_calls.append(dict(variables or {}))
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
        self.alert_fetch_limits.append(max_records)
        self._page_offset = max(int(start_offset or 0), 0)
        alert_ids = {str(item) for item in (variables.get("alertIds") or []) if item}
        vega_ids = {str(item) for item in (variables.get("vegaAlertIds") or []) if item}
        lookup_ids = alert_ids | vega_ids
        has_related = variables.get("hasRelatedIncidents")
        rows = []
        for alert in self.alerts:
            keys = {
                str(alert.get("id") or ""),
                str(alert.get("vegaAlertId") or ""),
                str(alert.get("alertId") or ""),
            }
            keys.discard("")
            if lookup_ids:
                if not keys.intersection(lookup_ids):
                    continue
            else:
                related = bool(alert.get("relatedIncidents") or [])
                if has_related is True and not related:
                    continue
                if has_related is False and related:
                    continue
            rows.append(alert)
        offset = getattr(self, "_page_offset", 0)
        if max_records is not None:
            return rows[offset : offset + int(max_records)]
        return rows[offset:]

    def count_alerts(self, variables):
        return len(self.get_alerts(variables))

    def count_incidents(self, variables):
        return len(self.get_incidents(variables))

    def get_all_alert_events(self, alert_id, page_size=None, max_records=None, deadline_monotonic=None, **_kwargs):
        self.event_calls.append(alert_id)
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
        if len(ids) > 10:
            raise AssertionError(f"alertIds batch of {len(ids)} exceeds 10")
        self.event_batch_calls.append(ids)
        self.event_calls.extend(ids)
        return {alert_id: list(self.alert_events.get(alert_id) or []) for alert_id in ids}

    def get_all_incident_timeline(self, incident_id, page_size=None, deadline_monotonic=None, **_kwargs):
        self.timeline_calls.append(incident_id)
        return list(self.timelines.get(incident_id) or [])

    def get_incident(self, incident_id):
        return dict(self.incident_by_id.get(incident_id) or {})


def _pipeline(
    manager: FakeManager,
    entities: str = "Alerts,Incidents",
    has_related: str = "Yes,No",
    max_fetch: int = 20,
    fetch_related_alert_metadata: bool = False,
):
    return IngestionPipeline(
        manager=manager,
        entities_raw=entities,
        lookback_minutes="5",
        backfill_days="0",
        has_related=has_related,
        fetch_related_alert_metadata=fetch_related_alert_metadata,
        max_fetch=max_fetch,
    )


def _sample_manager() -> FakeManager:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "labels": [{"name": "malware"}],
            "alerts": [
                {"alertId": "alert-1", "name": "Phish"},
                {"alertId": "alert-2", "name": "Beacon"},
            ],
        }
    ]
    manager.alerts = [
        {
            "id": "alert-1",
            "vegaAlertId": "VALERT-1",
            "name": "Phish",
            "relatedIncidents": [{"incidentId": "inc-1", "name": "Campaign"}],
        },
        {
            "id": "alert-2",
            "vegaAlertId": "VALERT-2",
            "name": "Beacon",
            "relatedIncidents": [{"incidentId": "inc-1", "name": "Campaign"}],
        },
        {"id": "alert-3", "vegaAlertId": "VALERT-3", "name": "Noise"},
    ]
    manager.alert_events = {
        "alert-1": [{"name": "evt-a"}],
        "alert-2": [{"name": "evt-b"}, {"name": "evt-c"}],
    }
    return manager


def _ids(summary: dict) -> list[str]:
    return [record.get("id") for _, record in summary["records"]]


def test_incident_related_alerts_share_one_grouping_id() -> None:
    manager = _sample_manager()
    summary = _pipeline(manager).run()
    records = summary["records"]
    related = [item for item in records if soar_meta(item[1]).get("is_incident_case")]
    unrelated = [item for item in records if not soar_meta(item[1]).get("is_incident_case")]
    assert len(related) == 3
    assert related[0][0] == ENTITY_TYPE_INCIDENT
    assert {item[0] for item in related[1:]} == {ENTITY_TYPE_ALERT}
    assert soar_meta(related[0][1])["grouping_id"] == "Vega:incident:inc-1"
    assert soar_meta(related[0][1])["case_part"] == 0
    assert all(soar_meta(item[1])["grouping_id"] == "Vega:incident:inc-1:related:cluster:1" for item in related[1:])
    assert all(soar_meta(item[1])["case_part"] == 1 for item in related[1:])
    titles = {soar_meta(item[1])["case_title"] for item in related}
    assert all(title.startswith("Vega Incident - VINC-1 - Campaign") for title in titles)
    assert "(related alerts)" not in soar_meta(related[0][1])["case_title"]
    assert all(soar_meta(item[1])["case_title"].endswith("(cluster 1)") for item in related[1:])
    assert soar_meta(related[0][1])["case_tags"] == ["malware"]
    assert all(soar_meta(item[1])["case_tags"] == ["malware"] for item in related)
    assert all(
        soar_meta(item[1])["incident_label_tags"] == ["malware"] for item in related if item[0] == ENTITY_TYPE_ALERT
    )
    assert soar_meta(unrelated[0][1])["case_tags"] == []
    assert "incident_label_tags" not in soar_meta(unrelated[0][1])
    assert [item[1]["id"] for item in related[1:]] == ["alert-1", "alert-2"]
    assert related[1][1]["vegaAlertId"] == "VALERT-1"
    assert related[2][1]["vegaAlertId"] == "VALERT-2"
    assert [evt["name"] for evt in related[1][1]["alert_events"]] == ["evt-a"]
    assert [evt["name"] for evt in related[2][1]["alert_events"]] == ["evt-b", "evt-c"]
    assert len(unrelated) == 1
    assert unrelated[0][1]["id"] == "alert-3"
    assert soar_meta(unrelated[0][1])["soar_alert_type"] == SOAR_ALERT_TYPE_ALERT
    assert soar_meta(unrelated[0][1])["grouping_id"] == "Vega:alert:alert-3"
    assert soar_meta(unrelated[0][1])["case_title"].startswith("Vega Alert - VALERT-3 - Noise")
    id_lookups = [call for call in manager.alert_calls if call.get("alertIds") or call.get("vegaAlertIds")]
    assert id_lookups
    looked_up = set()
    for call in id_lookups:
        looked_up.update(str(item) for item in (call.get("alertIds") or []) if item)
        looked_up.update(str(item) for item in (call.get("vegaAlertIds") or []) if item)
    assert {"alert-1", "alert-2"} <= looked_up
    assert not any("VEGA-" in str(item) for call in id_lookups for item in (call.get("alertIds") or []))
    assert "hasRelatedIncidents" not in id_lookups[0]
    assert "from" in id_lookups[0] or "updatedFrom" in id_lookups[0]
    unrelated_lookups = [call for call in manager.alert_calls if call.get("hasRelatedIncidents") is False]
    assert unrelated_lookups


def test_incident_related_and_unrelated_keep_own_labels() -> None:
    manager = _sample_manager()
    manager.incidents[0]["labels"] = [{"name": "campaign", "color": "#00aa00"}]
    manager.alerts[0]["labels"] = [{"name": "phish", "color": "#ff0000"}]
    manager.alerts[1]["labels"] = [{"name": "c2", "color": "#0000ff"}]
    manager.alerts[2]["labels"] = [{"name": "noise", "color": "#888888"}]
    summary = _pipeline(manager).run()
    by_id = {item[1]["id"]: item[1] for item in summary["records"]}
    assert by_id["inc-1"]["labels"] == [{"name": "campaign", "color": "#00aa00"}]
    assert by_id["alert-1"]["labels"] == [{"name": "phish", "color": "#ff0000"}]
    assert by_id["alert-2"]["labels"] == [{"name": "c2", "color": "#0000ff"}]
    assert by_id["alert-3"]["labels"] == [{"name": "noise", "color": "#888888"}]


def test_related_stub_does_not_inherit_incident_labels() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "labels": [{"name": "campaign", "color": "#00aa00"}],
            "alerts": [{"alertId": "alert-missing", "name": "Stub"}],
        }
    ]
    manager.alerts = []
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    related = [item[1] for item in summary["records"] if item[0] == ENTITY_TYPE_ALERT]
    assert related
    assert not related[0].get("labels")
    assert soar_meta(related[0])["case_tags"] == ["campaign"]


def test_related_stub_keeps_nested_incident_alert_labels() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "labels": [{"name": "campaign", "color": "#00aa00"}],
            "alerts": [
                {
                    "alertId": "alert-missing",
                    "vegaAlertId": "VEGA-2418",
                    "name": "Stub",
                    "labels": [{"name": "incident-33 related alert", "color": "BLUE"}],
                }
            ],
        }
    ]
    manager.alerts = []
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    related = [item[1] for item in summary["records"] if item[0] == ENTITY_TYPE_ALERT]
    assert related
    assert related[0]["labels"] == [{"name": "incident-33 related alert", "color": "BLUE"}]
    assert related[0]["vegaAlertId"] == "VEGA-2418"
    assert soar_meta(related[0])["case_tags"] == [
        "campaign",
        "incident-33 related alert",
    ]


def test_related_alert_keeps_own_labels_and_unions_tags() -> None:
    manager = _sample_manager()
    manager.incidents[0]["labels"] = [
        {"name": "incident", "color": "BLUE"},
        {"name": "IT", "color": "BLUE"},
    ]
    manager.alerts[0]["labels"] = [{"name": "incident-33 related alert", "color": "BLUE"}]
    manager.alerts[1]["labels"] = []
    summary = _pipeline(manager).run()
    by_id = {item[1]["id"]: item[1] for item in summary["records"]}
    assert by_id["inc-1"]["labels"] == [
        {"name": "incident", "color": "BLUE"},
        {"name": "IT", "color": "BLUE"},
    ]
    assert by_id["alert-1"]["labels"] == [{"name": "incident-33 related alert", "color": "BLUE"}]
    assert not by_id["alert-2"].get("labels")
    related = [item for item in summary["records"] if soar_meta(item[1]).get("is_incident_case")]
    assert soar_meta(related[0][1])["case_tags"] == ["incident", "IT"]
    assert soar_meta(by_id["alert-1"])["case_tags"] == [
        "incident",
        "IT",
        "incident-33 related alert",
    ]
    assert soar_meta(by_id["alert-2"])["case_tags"] == [
        "incident",
        "IT",
        "incident-33 related alert",
    ]
    assert soar_meta(by_id["alert-1"])["incident_label_tags"] == ["incident", "IT"]
    assert soar_meta(by_id["alert-2"])["incident_label_tags"] == ["incident", "IT"]
    assert "incident_label_tags" not in soar_meta(by_id["alert-3"])


def test_incident_case_unions_incident_and_related_alert_labels() -> None:
    manager = _sample_manager()
    manager.incidents[0]["labels"] = [{"name": "malware"}, {"name": "campaign"}]
    manager.alerts[0]["labels"] = [{"name": "phish"}, {"name": "malware"}]
    manager.alerts[1]["labels"] = [{"name": "c2"}]
    manager.alerts[2]["labels"] = [{"name": "noise"}]
    summary = _pipeline(manager).run()
    related = [item for item in summary["records"] if soar_meta(item[1]).get("is_incident_case")]
    unrelated = [item for item in summary["records"] if not soar_meta(item[1]).get("is_incident_case")]
    incident = [item for item in related if item[0] == ENTITY_TYPE_INCIDENT]
    related_alerts = [item for item in related if item[0] == ENTITY_TYPE_ALERT]
    assert all(soar_meta(item[1])["case_tags"] == ["malware", "campaign"] for item in incident)
    assert all(soar_meta(item[1])["case_tags"] == ["malware", "campaign", "phish", "c2"] for item in related_alerts)
    assert soar_meta(unrelated[0][1])["case_tags"] == ["noise"]
    assert unrelated[0][1]["labels"] == [{"name": "noise"}]


def test_incidents_alerts_yes_nests_related_and_skips_unrelated() -> None:
    manager = _sample_manager()
    summary = _pipeline(manager, entities="Incidents,Alerts", has_related="Yes").run()
    assert _ids(summary) == ["inc-1", "alert-1", "alert-2"]
    assert all(soar_meta(record).get("is_incident_case") for _, record in summary["records"])
    assert not any(call.get("hasRelatedIncidents") is False for call in manager.alert_calls)


def test_incidents_alerts_no_skips_nested_related_and_keeps_unrelated() -> None:
    manager = _sample_manager()
    summary = _pipeline(manager, has_related="No").run()
    ids = _ids(summary)
    assert ids == ["inc-1", "alert-3"]
    assert soar_meta(summary["records"][0][1])["soar_alert_type"] == SOAR_ALERT_TYPE_INCIDENT
    assert soar_meta(summary["records"][1][1])["grouping_id"] == "Vega:alert:alert-3"
    assert not any(call.get("alertIds") for call in manager.alert_calls)
    assert all(call.get("hasRelatedIncidents") is False for call in manager.alert_calls)


def test_incidents_only_skips_related_and_unrelated_alerts() -> None:
    manager = _sample_manager()
    for has_related in ("Yes", "No", "Yes,No"):
        manager.alert_calls = []
        manager.incident_calls = []
        summary = _pipeline(manager, entities="Incidents", has_related=has_related).run()
        assert _ids(summary) == ["inc-1"]
        assert not manager.alert_calls
        assert manager.incident_calls


def test_incident_query_uses_user_and_investigation_status_filters() -> None:
    manager = _sample_manager()
    pipeline = IngestionPipeline(
        manager=manager,
        entities_raw="Incidents",
        lookback_minutes="5",
        backfill_days="0",
        incident_user_statuses="OPEN, IN REVIEW",
        incident_investigation_statuses="NEW",
        max_fetch=20,
    )
    pipeline.run()
    assert manager.incident_calls
    call = manager.incident_calls[0]
    assert call["userStatuses"] == ["OPEN", "IN_REVIEW"]
    assert call["investigationStatuses"] == ["NEW"]
    assert "statuses" not in call


def test_alerts_yes_no_creates_standalone_related_and_unrelated() -> None:
    manager = _sample_manager()
    summary = _pipeline(manager, entities="Alerts", has_related="Yes,No").run()
    ids = _ids(summary)
    assert ids == ["alert-1", "alert-2", "alert-3"]
    assert not manager.incident_calls
    assert all(not soar_meta(record).get("is_incident_case") for _, record in summary["records"])
    assert {soar_meta(record)["grouping_id"] for _, record in summary["records"]} == {
        "Vega:alert:alert-1",
        "Vega:alert:alert-2",
        "Vega:alert:alert-3",
    }


def test_alerts_yes_creates_standalone_related_only() -> None:
    manager = _sample_manager()
    summary = _pipeline(manager, entities="Alerts", has_related="Yes").run()
    assert _ids(summary) == ["alert-1", "alert-2"]
    assert not manager.incident_calls
    assert all(call.get("hasRelatedIncidents") is True for call in manager.alert_calls)
    assert all(not soar_meta(record).get("is_incident_case") for _, record in summary["records"])
    assert soar_meta(summary["records"][0][1])["grouping_id"] == "Vega:alert:alert-1"


def test_alerts_no_creates_standalone_unrelated_only() -> None:
    manager = _sample_manager()
    summary = _pipeline(manager, entities="Alerts", has_related="No").run()
    ids = _ids(summary)
    assert ids == ["alert-3"]
    assert not manager.incident_calls
    assert all(call.get("hasRelatedIncidents") is False for call in manager.alert_calls)
    assert soar_meta(summary["records"][0][1])["case_title"].startswith("Vega Alert - VALERT-3 - Noise")
    assert soar_meta(summary["records"][0][1])["grouping_id"] == "Vega:alert:alert-3"


def test_singular_entity_names_match_alerts_and_incidents() -> None:
    manager = _sample_manager()
    summary = _pipeline(manager, entities="Incident, Alert", has_related="Yes,No").run()
    assert _ids(summary) == ["inc-1", "alert-1", "alert-2", "alert-3"]


def test_short_nested_alert_list_backfills_related_alerts() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "createdAt": "2026-07-28T11:22:43Z",
            "lastUpdated": "2026-07-29T01:00:00Z",
            "alertsCount": 3,
            "alerts": [{"alertId": "alert-1", "name": "Phish"}],
        }
    ]
    manager.alerts = [
        {
            "id": "alert-1",
            "vegaAlertId": "VALERT-1",
            "name": "Phish",
            "createdAt": "2026-01-01T00:00:00Z",
            "relatedIncidents": [{"incidentId": "inc-1"}],
        },
        {
            "id": "alert-2",
            "vegaAlertId": "VALERT-2",
            "name": "Beacon",
            "createdAt": "2026-02-01T00:00:00Z",
            "relatedIncidents": [
                {"incidentId": "other"},
                {"incidentId": "inc-1"},
            ],
        },
        {
            "id": "alert-3",
            "vegaAlertId": "VALERT-3",
            "name": "Noise",
            "createdAt": "2026-03-01T00:00:00Z",
            "relatedIncidents": [{"incidentId": "other"}],
        },
    ]
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    assert _ids(summary) == ["inc-1", "alert-1", "alert-2"]
    related = [item[1] for item in summary["records"] if item[0] == ENTITY_TYPE_ALERT]
    assert {soar_meta(item)["grouping_id"] for item in related} == {"Vega:incident:inc-1:related:cluster:1"}
    assert {soar_meta(item)["grouping_start"] for item in related} == {"2026-07-28T11:22:43Z"}
    assert {soar_meta(item)["grouping_end"] for item in related} == {"2026-07-29T01:00:00Z"}
    assert any(call.get("hasRelatedIncidents") is True for call in manager.alert_calls)
    backfill_calls = [
        call for call in manager.alert_calls if call.get("hasRelatedIncidents") is True and not call.get("alertIds")
    ]
    assert backfill_calls
    assert "alertSeverities" not in backfill_calls[0]
    assert "statuses" not in backfill_calls[0]
    assert "alertVerdicts" not in backfill_calls[0]
    assert "inc-1" not in summary["checkpoint"]["related_backfill"]["open"]


def test_by_id_incident_replaces_truncated_nested_alert_ids() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "alertsCount": 3,
            "alerts": [{"alertId": "alert-1", "name": "Phish"}],
        }
    ]
    manager.incident_by_id["inc-1"] = {
        "id": "inc-1",
        "alertsCount": 3,
        "alerts": [
            {"alertId": "alert-1", "name": "Phish"},
            {"alertId": "alert-2", "name": "Beacon"},
            {"alertId": "alert-3", "name": "Noise"},
        ],
    }
    manager.alerts = [
        {
            "id": f"alert-{index}",
            "name": f"A{index}",
            "relatedIncidents": [{"incidentId": "inc-1"}],
        }
        for index in range(1, 4)
    ]
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    assert _ids(summary) == ["inc-1", "alert-1", "alert-2", "alert-3"]
    backfill_calls = [
        call for call in manager.alert_calls if call.get("hasRelatedIncidents") is True and not call.get("alertIds")
    ]
    assert not backfill_calls
    assert summary["checkpoint"]["related_backfill"]["settled"].get("inc-1") == 3


def test_every_related_alert_id_is_fetched_and_packaged() -> None:
    total = 12
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "alertsCount": total,
            "alerts": [{"alertId": f"alert-{index}"} for index in range(1, total + 1)],
        }
    ]
    manager.alerts = [{"id": f"alert-{index}", "name": f"A{index}"} for index in range(1, total + 1)]
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes", max_fetch=200).run()
    packaged = [item for item in _ids(summary) if str(item).startswith("alert-")]
    assert packaged == [f"alert-{index}" for index in range(1, total + 1)]
    requested = {
        str(item) for call in manager.alert_calls for item in (call.get("alertIds") or call.get("vegaAlertIds") or [])
    }
    assert requested == {f"alert-{index}" for index in range(1, total + 1)}
    assert "inc-1" not in summary["checkpoint"]["related_backfill"]["open"]
    assert summary["checkpoint"]["related_backfill"]["settled"]["inc-1"] == total


def test_related_alerts_are_batched_by_ninety_in_one_run() -> None:
    import core.IngestionPipeline as pipeline_module

    previous_case = pipeline_module.MAX_ALERTS_PER_CASE
    pipeline_module.MAX_ALERTS_PER_CASE = 2
    try:
        total = 6
        manager = FakeManager()
        manager.incidents = [
            {
                "id": "inc-1",
                "vegaUniqueIncidentId": "INC-34",
                "name": "Campaign",
                "alertsCount": total,
                "alerts": [{"alertId": f"alert-{index}"} for index in range(1, total + 1)],
            }
        ]
        manager.alerts = [{"id": f"alert-{index}", "name": f"A{index}"} for index in range(1, total + 1)]
        summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes", max_fetch=50).run()
        alerts = [item for item in summary["records"] if item[0] == ENTITY_TYPE_ALERT]
        assert [item[1]["id"] for item in alerts] == [f"alert-{index}" for index in range(1, total + 1)]
        assert [soar_meta(item[1])["grouping_id"] for item in alerts] == [
            "Vega:incident:inc-1:related:cluster:1",
            "Vega:incident:inc-1:related:cluster:1",
            "Vega:incident:inc-1:related:cluster:2",
            "Vega:incident:inc-1:related:cluster:2",
            "Vega:incident:inc-1:related:cluster:3",
            "Vega:incident:inc-1:related:cluster:3",
        ]
        assert summary["checkpoint"]["related_backfill"]["settled"]["inc-1"] == total
        assert "inc-1" not in summary["checkpoint"]["related_backfill"]["open"]
    finally:
        pipeline_module.MAX_ALERTS_PER_CASE = previous_case


def test_related_batch_numbers_continue_from_checkpoint() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "INC-34",
            "name": "Campaign",
            "alertsCount": 3,
            "alerts": [{"alertId": f"alert-{index}"} for index in range(1, 4)],
        }
    ]
    manager.alerts = [{"id": f"alert-{index}", "name": f"A{index}"} for index in range(1, 4)]
    checkpoint = {
        "ingested_ids": ["incident:inc-1", "alert-1", "alert-2"],
        "related_backfill": {
            "offset": 0,
            "open": {},
            "settled": {"inc-1": 2},
            "batch_version": 5,
            "next_related_batch": {"inc-1": 3},
            "related_batch_filled": {"inc-1": 0},
        },
    }
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes", max_fetch=20).run(
        checkpoint=checkpoint
    )
    alerts = [record for kind, record in summary["records"] if kind == ENTITY_TYPE_ALERT]
    assert len(alerts) == 1
    meta = soar_meta(alerts[0])
    assert meta["grouping_id"] == "Vega:incident:inc-1:related:cluster:3"
    assert meta["case_title"].endswith("(cluster 3)")
    backfill = summary["checkpoint"]["related_backfill"]
    assert backfill["next_related_batch"]["inc-1"] == 3
    assert backfill["related_batch_filled"]["inc-1"] == 1


def test_missing_id_from_batch_is_fetched_on_its_own_and_packaged() -> None:
    class DropSecond(FakeManager):
        def get_alerts(self, variables, max_records=None, deadline_monotonic=None, start_offset=0, **kwargs):
            rows = super().get_alerts(variables, max_records, deadline_monotonic, start_offset, **kwargs)
            requested = [
                str(item) for item in (variables.get("alertIds") or variables.get("vegaAlertIds") or []) if item
            ]
            if len(requested) > 1:
                return [row for row in rows if row.get("id") != "alert-2"]
            return rows

    manager = DropSecond()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "alertsCount": 3,
            "alerts": [
                {"alertId": "alert-1"},
                {"alertId": "alert-2"},
                {"alertId": "alert-3"},
            ],
        }
    ]
    manager.alerts = [{"id": f"alert-{index}", "name": f"A{index}"} for index in range(1, 4)]
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes", max_fetch=20).run()
    assert [item for item in _ids(summary) if str(item).startswith("alert-")] == [
        "alert-1",
        "alert-2",
        "alert-3",
    ]
    singleton = [
        call.get("alertIds") or call.get("vegaAlertIds")
        for call in manager.alert_calls
        if len(call.get("alertIds") or call.get("vegaAlertIds") or []) == 1
    ]
    assert ["alert-2"] in singleton


def test_checkpointed_related_alerts_are_fetched_and_packaged_again() -> None:
    total = 3
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "INC-34",
            "name": "Campaign",
            "alertsCount": total,
            "alerts": [{"alertId": f"alert-{index}"} for index in range(1, total + 1)],
        }
    ]
    manager.alerts = [{"id": f"alert-{index}", "name": f"A{index}"} for index in range(1, total + 1)]
    checkpoint = {
        "ingested_ids": ["incident:inc-1"] + [f"alert-{index}" for index in range(1, total + 1)],
        "related_backfill": {
            "offset": 0,
            "open": {},
            "settled": {"inc-1": total},
            "batch_version": 1,
        },
    }
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes", max_fetch=20).run(
        checkpoint=checkpoint
    )
    sent = [item for item in _ids(summary) if str(item).startswith("alert-")]
    assert set(sent) == {f"alert-{index}" for index in range(1, total + 1)}
    requested = {
        str(item) for call in manager.alert_calls for item in (call.get("alertIds") or call.get("vegaAlertIds") or [])
    }
    assert requested == {f"alert-{index}" for index in range(1, total + 1)}
    assert summary["checkpoint"]["related_backfill"]["settled"]["inc-1"] == total


def test_truncated_related_scan_resumes_remaining_alerts() -> None:
    class OnePage(FakeManager):
        def __init__(self) -> None:
            super().__init__()
            self.backfill_calls = 0

        def get_alerts(
            self,
            variables,
            max_records=None,
            deadline_monotonic=None,
            start_offset=0,
            **kwargs,
        ):
            if variables.get("hasRelatedIncidents") is True and not variables.get("alertIds"):
                self.backfill_calls += 1
                rows = super().get_alerts(
                    variables,
                    max_records=None,
                    deadline_monotonic=deadline_monotonic,
                    start_offset=0,
                )
                page = rows[int(start_offset or 0) :]
                if self.backfill_calls == 1:
                    self.last_fetch_truncated = True
                    return page[:1]
                self.last_fetch_truncated = False
                if max_records is not None:
                    return page[: int(max_records)]
                return page
            return super().get_alerts(
                variables,
                max_records,
                deadline_monotonic,
                start_offset,
                **kwargs,
            )

    manager = OnePage()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "alertsCount": 4,
            "alerts": [{"alertId": "alert-1", "name": "Phish"}],
        }
    ]
    manager.alerts = [
        {
            "id": f"alert-{index}",
            "name": f"A{index}",
            "relatedIncidents": [{"incidentId": "inc-1"}],
        }
        for index in range(1, 5)
    ]
    first = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    first_alerts = [item for item in _ids(first) if str(item).startswith("alert-")]
    assert first_alerts == ["alert-1"]
    progress = first["checkpoint"]["related_backfill"]
    assert progress["open"]["inc-1"]["have"] == 1
    assert progress["open"]["inc-1"]["expected"] == 4
    assert progress["offset"] == 1
    second = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run(checkpoint=first["checkpoint"])
    assert _ids(second) == ["alert-2", "alert-3", "alert-4"]
    assert "inc-1" not in second["checkpoint"]["related_backfill"]["open"]
    assert second["checkpoint"]["related_backfill"]["settled"]["inc-1"] == 4
    related = [item[1] for item in second["records"]]
    assert {soar_meta(item)["grouping_id"] for item in related} == {"Vega:incident:inc-1:related:cluster:1"}


def test_many_related_alerts_share_one_grouping_id() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "alerts": [
                {"alertId": "alert-1"},
                {"alertId": "alert-2"},
                {"alertId": "alert-3"},
                {"alertId": "alert-4"},
                {"alertId": "alert-5"},
            ],
        }
    ]
    manager.alerts = [{"id": f"alert-{index}", "name": f"A{index}"} for index in range(1, 6)]
    summary = _pipeline(
        manager,
        entities="Alerts,Incidents",
        has_related="Yes",
        max_fetch=20,
    ).run()
    records = summary["records"]
    assert [kind for kind, _ in records] == [
        ENTITY_TYPE_INCIDENT,
        ENTITY_TYPE_ALERT,
        ENTITY_TYPE_ALERT,
        ENTITY_TYPE_ALERT,
        ENTITY_TYPE_ALERT,
        ENTITY_TYPE_ALERT,
    ]
    groupings = [soar_meta(record)["grouping_id"] for _, record in records]
    parts = [soar_meta(record).get("case_part") for _, record in records]
    titles = [soar_meta(record)["case_title"] for _, record in records]
    assert all(title.startswith("Vega Incident - VINC-1 - Campaign") for title in titles)
    assert "(related alerts)" not in titles[0]
    assert all(title.endswith("(cluster 1)") for title in titles[1:])
    assert groupings == [
        "Vega:incident:inc-1",
        "Vega:incident:inc-1:related:cluster:1",
        "Vega:incident:inc-1:related:cluster:1",
        "Vega:incident:inc-1:related:cluster:1",
        "Vega:incident:inc-1:related:cluster:1",
        "Vega:incident:inc-1:related:cluster:1",
    ]
    assert parts == [0, 1, 1, 1, 1, 1]
    assert [record.get("id") for kind, record in records if kind == ENTITY_TYPE_INCIDENT] == ["inc-1"]
    assert [record.get("id") for kind, record in records if kind == ENTITY_TYPE_ALERT] == [
        "alert-1",
        "alert-2",
        "alert-3",
        "alert-4",
        "alert-5",
    ]


def test_related_case_unions_incident_and_alert_labels() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "labels": [{"name": "campaign"}],
            "alerts": [{"alertId": f"alert-{index}"} for index in range(1, 6)],
        }
    ]
    manager.alerts = [
        {"id": "alert-1", "name": "A1", "labels": [{"name": "phish"}]},
        {"id": "alert-2", "name": "A2", "labels": [{"name": "c2"}]},
        {"id": "alert-3", "name": "A3", "labels": [{"name": "beacon"}]},
        {"id": "alert-4", "name": "A4"},
        {"id": "alert-5", "name": "A5", "labels": [{"name": "persist"}]},
    ]
    summary = _pipeline(
        manager,
        entities="Alerts,Incidents",
        has_related="Yes",
        max_fetch=20,
    ).run()
    incident_tags = [
        soar_meta(record)["case_tags"] for kind, record in summary["records"] if kind == ENTITY_TYPE_INCIDENT
    ]
    related_tags = [
        soar_meta(record)["case_tags"] for _, record in summary["records"] if soar_meta(record).get("case_part") == 1
    ]
    assert incident_tags == [["campaign"]]
    assert related_tags == [["campaign", "phish", "c2", "beacon", "persist"]] * 5
    related = [record for kind, record in summary["records"] if kind == ENTITY_TYPE_ALERT]
    assert all(soar_meta(record)["incident_label_tags"] == ["campaign"] for record in related)
    assert not related[3].get("labels")
    assert related[0]["labels"] == [{"name": "phish"}]
    assert related[4]["labels"] == [{"name": "persist"}]


def test_two_incidents_one_related_and_overflow() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-small",
            "vegaUniqueIncidentId": "VINC-S",
            "name": "Small",
            "alerts": [{"alertId": "small-1"}],
        },
        {
            "id": "inc-large",
            "vegaUniqueIncidentId": "VINC-L",
            "name": "Large",
            "alerts": [{"alertId": f"large-{index}"} for index in range(1, 6)],
        },
    ]
    manager.alerts = [{"id": "small-1", "name": "Only"}] + [
        {"id": f"large-{index}", "name": f"L{index}"} for index in range(1, 6)
    ]
    manager.alert_events = {"small-1": [{"name": "evt-small"}]}
    summary = _pipeline(
        manager,
        entities="Alerts,Incidents",
        has_related="Yes",
        max_fetch=20,
    ).run()
    records = summary["records"]
    small = [item for item in records if soar_meta(item[1]).get("incident_id") == "inc-small"]
    large = [item for item in records if soar_meta(item[1]).get("incident_id") == "inc-large"]
    assert [kind for kind, _ in small] == [ENTITY_TYPE_INCIDENT, ENTITY_TYPE_ALERT]
    assert small[1][1]["id"] == "small-1"
    assert [evt["name"] for evt in small[1][1]["alert_events"]] == ["evt-small"]
    assert soar_meta(small[0][1])["grouping_id"] == "Vega:incident:inc-small"
    assert soar_meta(small[1][1])["grouping_id"] == "Vega:incident:inc-small:related:cluster:1"
    assert [kind for kind, _ in large] == [
        ENTITY_TYPE_INCIDENT,
        ENTITY_TYPE_ALERT,
        ENTITY_TYPE_ALERT,
        ENTITY_TYPE_ALERT,
        ENTITY_TYPE_ALERT,
        ENTITY_TYPE_ALERT,
    ]
    assert [soar_meta(item[1]).get("case_part") for item in large] == [0, 1, 1, 1, 1, 1]
    assert {soar_meta(item[1])["grouping_id"] for item in large[1:]} == {"Vega:incident:inc-large:related:cluster:1"}
    assert [record.get("id") for kind, record in large if kind == ENTITY_TYPE_INCIDENT] == ["inc-large"]


def test_incident_without_related_alerts_creates_incident_package() -> None:
    manager = FakeManager()
    manager.incidents = [{"id": "inc-empty", "vegaUniqueIncidentId": "VINC-E", "name": "Empty"}]
    summary = _pipeline(manager, entities="Incidents").run()
    assert len(summary["records"]) == 1
    entity_type, record = summary["records"][0]
    assert entity_type == ENTITY_TYPE_INCIDENT
    assert soar_meta(record)["soar_alert_type"] == SOAR_ALERT_TYPE_INCIDENT
    assert soar_meta(record)["grouping_id"] == "Vega:incident:inc-empty"
    assert soar_meta(record)["case_title"].startswith("Vega Incident - VINC-E - Empty")


def test_related_alert_lookup_does_not_send_vega_ids_as_graphql_ids() -> None:
    uuid = "019e1b27-5119-7822-bde3-344b13e481cf"

    class StrictManager(FakeManager):
        def get_alerts(self, variables, max_records=None, **kwargs):
            alert_ids = [str(item) for item in (variables.get("alertIds") or []) if item]
            if any(not item.count("-") == 4 for item in alert_ids):
                raise RuntimeError(f"alertIds must be UUIDs, got {alert_ids}")
            return super().get_alerts(variables, max_records, **kwargs)

    manager = StrictManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "alerts": [
                {"alertId": uuid, "vegaAlertId": "VEGA-3219", "name": "Phish"},
            ],
        }
    ]
    manager.alerts = [
        {
            "id": uuid,
            "vegaAlertId": "VEGA-3219",
            "name": "Phish",
            "labels": [{"name": "phish", "color": "#ff0000"}],
        }
    ]
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    related = [item[1] for item in summary["records"] if item[0] == ENTITY_TYPE_ALERT]
    assert related
    assert related[0]["labels"] == [{"name": "phish", "color": "#ff0000"}]
    id_lookups = [call for call in manager.alert_calls if call.get("alertIds")]
    assert id_lookups
    assert all(all(item.count("-") == 4 for item in call["alertIds"]) for call in id_lookups)
    assert related[0]["id"] == uuid


def test_related_alert_labels_survive_when_uuid_lookup_fails() -> None:
    uuid = "019e1b27-5119-7822-bde3-344b13e481cf"

    class UuidLookupFails(FakeManager):
        def get_alerts(self, variables, max_records=None, **kwargs):
            if variables.get("alertIds"):
                raise RuntimeError("getAlerts(alertIds) rejected mixed IDs")
            vega_ids = {str(item) for item in (variables.get("vegaAlertIds") or []) if item}
            if vega_ids:
                rows = [alert for alert in self.alerts if str(alert.get("vegaAlertId") or "") in vega_ids]
                self.alert_calls.append(dict(variables or {}))
                if max_records is not None:
                    return rows[:max_records]
                return rows
            return super().get_alerts(variables, max_records, **kwargs)

    manager = UuidLookupFails()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Campaign",
            "alerts": [{"alertId": uuid, "vegaAlertId": "VEGA-3219", "name": "Phish"}],
        }
    ]
    manager.alerts = [
        {
            "id": uuid,
            "vegaAlertId": "VEGA-3219",
            "name": "Phish",
            "labels": [{"name": "phish"}],
        }
    ]
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    related = [item[1] for item in summary["records"] if item[0] == ENTITY_TYPE_ALERT]
    assert related[0]["labels"] == [{"name": "phish"}]


def test_related_alerts_are_not_ingested_twice_when_both_entities_selected() -> None:
    manager = FakeManager()
    manager.incidents = [{"id": "inc-1", "name": "Campaign", "alerts": [{"alertId": "alert-1"}]}]
    manager.alerts = [
        {
            "id": "alert-1",
            "name": "Phish",
            "relatedIncidents": [{"incidentId": "inc-1"}],
        }
    ]
    summary = _pipeline(manager).run()
    ids = [rec.get("id") for _, rec in summary["records"]]
    assert ids == ["inc-1", "alert-1"]
    assert all(soar_meta(rec)["is_incident_case"] for _, rec in summary["records"])


def test_unrelated_fetch_failure_still_emits_incident_cases() -> None:
    class BoomManager(FakeManager):
        def get_alerts(self, variables, max_records=None, **kwargs):
            if variables.get("hasRelatedIncidents") is False:
                raise RuntimeError("getAlerts boom")
            return super().get_alerts(variables, max_records, **kwargs)

    manager = BoomManager()
    manager.incidents = [{"id": "inc-1", "name": "Campaign", "alerts": [{"alertId": "alert-1"}]}]
    manager.alerts = [{"id": "alert-1", "name": "Phish"}]
    summary = _pipeline(manager, has_related="Yes,No").run()
    ids = [record.get("id") for _, record in summary["records"]]
    assert ids == ["inc-1", "alert-1"]
    assert summary["incomplete"] is True


def test_checkpoint_skips_already_ingested_records() -> None:
    manager = FakeManager()
    manager.incidents = [{"id": "inc-1", "name": "Campaign"}]
    manager.alerts = [{"id": "alert-3", "vegaAlertId": "VALERT-3", "name": "Noise"}]
    first = _pipeline(manager).run()
    second = _pipeline(manager).run(checkpoint=first["checkpoint"])
    assert first["fetched"] >= 1
    assert second["fetched"] == 0


def test_related_alert_name_uses_vega_alert_id_not_uuid() -> None:
    uuid = "019e1b27-5119-7822-bde3-344b13e481cf"
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "alerts": [{"alertId": uuid, "name": "Persist"}],
        }
    ]
    manager.alerts = [
        {
            "id": uuid,
            "vegaAlertId": "VALERT-9",
            "name": "Persist",
            "relatedIncidents": [{"incidentId": "inc-1"}],
        }
    ]
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    related = [item for item in summary["records"] if item[0] == ENTITY_TYPE_ALERT]
    assert len(related) == 1
    assert related[0][1]["vegaAlertId"] == "VALERT-9"
    from core.mapping import case_display_name

    assert case_display_name(related[0][1], ENTITY_TYPE_ALERT).startswith("Vega Alert - VALERT-9 - Persist")
    assert uuid not in case_display_name(related[0][1], ENTITY_TYPE_ALERT)


def test_alert_id_lookup_falls_back_to_related_window_query() -> None:
    class EmptyIdManager(FakeManager):
        def get_alerts(self, variables, max_records=None, **kwargs):
            variables = dict(variables or {})
            if variables.get("alertIds") or variables.get("vegaAlertIds"):
                self.alert_calls.append(variables)
                return []
            return super().get_alerts(variables, max_records, **kwargs)

    manager = EmptyIdManager()
    manager.incidents = [{"id": "inc-1", "name": "Campaign", "alerts": [{"alertId": "alert-1"}]}]
    manager.alerts = [
        {
            "id": "alert-1",
            "name": "Phish",
            "relatedIncidents": [{"incidentId": "inc-1"}],
        }
    ]
    summary = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    ids = [record.get("id") for _, record in summary["records"]]
    assert ids == ["inc-1", "alert-1"]
    assert any(call.get("hasRelatedIncidents") is True for call in manager.alert_calls)


def test_every_related_alert_fetches_events() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Campaign",
            "alerts": [{"alertId": f"alert-{i}"} for i in range(1, 6)],
        }
    ]
    manager.alerts = [{"id": f"alert-{i}", "name": f"A{i}"} for i in range(1, 6)]
    manager.alert_events = {f"alert-{i}": [{"name": f"e{i}"}] for i in range(1, 6)}
    summary = _pipeline(
        manager,
        entities="Alerts,Incidents",
        has_related="Yes",
        max_fetch=20,
    ).run()
    related = [item for item in summary["records"] if item[0] == ENTITY_TYPE_ALERT]
    assert len(related) == 5
    assert manager.event_batch_calls == [[f"alert-{i}" for i in range(1, 6)]]
    assert manager.event_calls == [f"alert-{i}" for i in range(1, 6)]
    by_id = {item[1]["id"]: item[1]["alert_events"] for item in related}
    for index in range(1, 6):
        assert [evt["name"] for evt in by_id[f"alert-{index}"]] == [f"e{index}"]
    assert summary["incomplete"] is False
    assert summary["checkpoint"]["incomplete"] is False


def _event_uuid(index: int) -> str:
    return f"019e1b27-5119-7822-bde3-{index:012d}"


def test_related_alert_events_are_batched_by_ten_and_not_mixed() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Campaign",
            "alerts": [{"alertId": _event_uuid(index)} for index in range(1, 13)],
        }
    ]
    manager.alerts = [{"id": _event_uuid(index), "name": f"A{index}"} for index in range(1, 13)]
    manager.alert_events = {_event_uuid(index): [{"name": f"e{index}"}] for index in range(1, 13)}
    summary = _pipeline(
        manager,
        entities="Alerts,Incidents",
        has_related="Yes",
        max_fetch=20,
    ).run()
    related = [item for item in summary["records"] if item[0] == ENTITY_TYPE_ALERT]
    assert [len(batch) for batch in manager.event_batch_calls] == [10, 2]
    assert all(len(batch) <= 10 for batch in manager.event_batch_calls)
    by_id = {item[1]["id"]: item[1]["alert_events"] for item in related}
    assert len(by_id) == 12
    for index in range(1, 13):
        assert [evt["name"] for evt in by_id[_event_uuid(index)]] == [f"e{index}"]


def test_timeout_saves_watermark_and_next_run_continues() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Campaign",
            "createdAt": "2026-01-01T00:00:00Z",
            "lastUpdated": "2026-01-01T00:00:00Z",
            "alerts": [{"alertId": "alert-1"}, {"alertId": "alert-2"}],
        }
    ]
    manager.alerts = [
        {
            "id": "alert-1",
            "name": "A1",
            "createdAt": "2026-01-02T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
            "relatedIncidents": [{"incidentId": "inc-1"}],
        },
        {
            "id": "alert-2",
            "name": "A2",
            "createdAt": "2026-01-03T00:00:00Z",
            "updatedAt": "2026-01-03T00:00:00Z",
            "relatedIncidents": [{"incidentId": "inc-1"}],
        },
    ]
    manager.alert_events = {
        "alert-1": [{"name": "e1"}],
        "alert-2": [{"name": "e2"}],
    }
    pipeline = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes", max_fetch=20)
    original_append = pipeline._append_incident_alert

    def _append_then_expire(*args, **kwargs):
        added = original_append(*args, **kwargs)
        if added:
            pipeline._deadline = 0
        return added

    pipeline._append_incident_alert = _append_then_expire
    first = pipeline.run(deadline_monotonic=time.monotonic() + 60)
    assert first["incomplete"] is True
    assert [kind for kind, _ in first["records"]] == [ENTITY_TYPE_INCIDENT]
    assert first["checkpoint"]["watermark"] == "2026-01-01T00:00:00Z"
    assert first["checkpoint"]["incomplete"] is True
    assert first["checkpoint"]["query_mode"] == "created"
    assert manager.timeline_calls == ["inc-1"]

    second = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes", max_fetch=20).run(
        checkpoint=first["checkpoint"]
    )
    ids = [record.get("id") for _, record in second["records"]]
    assert ids == ["alert-1", "alert-2"]
    assert [item[1]["alert_events"][0]["name"] for item in second["records"]] == [
        "e1",
        "e2",
    ]
    assert second["incomplete"] is False
    assert manager.timeline_calls == ["inc-1"]


def test_incomplete_created_window_keeps_createdat_filters() -> None:
    from datetime import datetime, timezone

    from core.utils import compute_time_window

    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    window = compute_time_window(
        {
            "watermark": "2026-01-01T00:00:00Z",
            "incomplete": True,
            "query_mode": "created",
        },
        backfill_days=0,
        lookback_minutes=5,
        now=now,
    )
    assert window["query_mode"] == "created"
    assert window["from"] is not None
    assert window["updated_from"] is None
    assert window["origin_from"] == window["from"]


def test_poisoned_checkpoint_rescans_created_backfill_not_updatedat() -> None:
    from datetime import datetime, timezone

    from core.utils import compute_time_window

    now = datetime(2026, 9, 18, 8, 30, 14, tzinfo=timezone.utc)
    window = compute_time_window(
        {
            "watermark": "2026-09-18T08:30:14Z",
            "incomplete": False,
            "query_mode": "updated",
            "ingested_ids": ["incident:inc-1"],
        },
        backfill_days=365,
        lookback_minutes=5,
        now=now,
    )
    assert window["query_mode"] == "created"
    assert window["updated_from"] is None
    assert window["from"] == "2025-09-18T08:25:14Z"
    assert window["to"] == "2026-09-18T08:30:14Z"

    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Already ingested",
            "createdAt": "2026-01-01T00:00:00Z",
        },
        {
            "id": "inc-2",
            "name": "Pending",
            "createdAt": "2026-02-01T00:00:00Z",
        },
    ]
    summary = _pipeline(manager, entities="Incidents").run(
        checkpoint={
            "watermark": "2026-09-18T08:30:14Z",
            "incomplete": False,
            "query_mode": "updated",
            "ingested_ids": ["incident:inc-1"],
        }
    )
    assert [record.get("id") for _, record in summary["records"]] == ["inc-2"]
    assert "from" in manager.incident_calls[0]
    assert "updatedFrom" not in manager.incident_calls[0]
    assert summary["checkpoint"]["origin_from"]


def test_caught_up_checkpoint_uses_updatedat_window() -> None:
    from datetime import datetime, timezone

    from core.utils import compute_time_window

    now = datetime(2026, 9, 18, 8, 30, 14, tzinfo=timezone.utc)
    window = compute_time_window(
        {
            "watermark": "2026-09-18T08:30:14Z",
            "incomplete": False,
            "query_mode": "updated",
            "origin_from": "2025-09-18T08:25:14Z",
            "ingested_ids": ["incident:inc-1"],
        },
        backfill_days=365,
        lookback_minutes=5,
        now=now,
    )
    assert window["query_mode"] == "updated"
    assert window["from"] is None
    assert window["updated_from"] == "2026-09-18T08:25:14Z"


def test_timeout_with_zero_packaged_keeps_previous_watermark() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Campaign",
            "createdAt": "2026-01-02T00:00:00Z",
            "lastUpdated": "2026-01-02T00:00:00Z",
        }
    ]
    checkpoint = {
        "watermark": "2026-01-01T00:00:00Z",
        "incomplete": True,
        "query_mode": "created",
        "ingested_ids": ["incident:inc-old"],
    }
    summary = _pipeline(manager, entities="Incidents").run(checkpoint=checkpoint, deadline_monotonic=0)
    assert summary["fetched"] == 0
    assert summary["incomplete"] is True
    assert summary["checkpoint"]["watermark"] == "2026-01-01T00:00:00Z"
    assert summary["checkpoint"]["incomplete"] is True
    assert summary["checkpoint"]["query_mode"] == "created"
    assert not manager.incident_calls


def test_fetch_error_keeps_previous_watermark() -> None:
    class BoomIncidents(FakeManager):
        def get_incidents(self, variables, max_records=None, **_kwargs):
            raise RuntimeError("getIncidents boom")

    checkpoint = {
        "watermark": "2026-01-01T00:00:00Z",
        "incomplete": True,
        "query_mode": "created",
        "ingested_ids": [],
    }
    summary = _pipeline(BoomIncidents(), entities="Incidents").run(checkpoint=checkpoint)
    assert summary["fetched"] == 0
    assert summary["incomplete"] is True
    assert summary["checkpoint"]["watermark"] == "2026-01-01T00:00:00Z"
    assert summary["checkpoint"]["query_mode"] == "created"


def test_truncated_fetch_stays_incomplete_after_packaging_returned_rows() -> None:
    class TruncatedManager(FakeManager):
        def get_incidents(self, variables, max_records=None, **_kwargs):
            self.incident_calls.append(dict(variables or {}))
            self.last_fetch_truncated = True
            return list(self.incidents[:1])

    manager = TruncatedManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Older",
            "createdAt": "2026-01-01T00:00:00Z",
            "lastUpdated": "2026-01-01T00:00:00Z",
        },
        {
            "id": "inc-2",
            "name": "Newer",
            "createdAt": "2026-06-01T00:00:00Z",
            "lastUpdated": "2026-06-01T00:00:00Z",
        },
    ]
    summary = _pipeline(manager, entities="Incidents", max_fetch=20).run()
    assert [record.get("id") for _, record in summary["records"]] == ["inc-1"]
    assert summary["incomplete"] is True
    assert summary["checkpoint"]["watermark"] == "2026-01-01T00:00:00Z"
    assert summary["checkpoint"]["incomplete"] is True
    assert summary["checkpoint"]["query_mode"] == "created"
    assert summary["checkpoint"]["watermark"] != summary["window"]["end"]


def test_preview_counts_and_samples_without_enrichment() -> None:
    manager = _sample_manager()
    preview = _pipeline(manager, max_fetch=5).preview(sample_limit=5)
    assert preview["incident_count"] == 1
    assert preview["related_alert_count"] == 2
    assert preview["unrelated_alert_count"] == 1
    assert preview["total_alert_count"] == 3
    assert preview["include_incidents"] is True
    assert preview["include_related"] is True
    assert preview["include_unrelated"] is True
    kinds = [kind for kind, _ in preview["records"]]
    assert ENTITY_TYPE_INCIDENT in kinds
    assert ENTITY_TYPE_ALERT in kinds
    assert manager.event_calls == []
    assert manager.timeline_calls == []
    assert all("alert_events" not in record for _, record in preview["records"])
    assert all("timeline" not in record for _, record in preview["records"])


def test_preview_samples_follow_entity_selection() -> None:
    manager = _sample_manager()
    preview = _pipeline(manager, entities="Incidents", has_related="Yes,No", max_fetch=5).preview(sample_limit=5)
    assert preview["incident_count"] == 1
    assert preview["related_alert_count"] == 0
    assert preview["unrelated_alert_count"] == 0
    assert preview["total_alert_count"] == 0
    assert preview["include_incidents"] is True
    assert preview["include_related"] is False
    assert preview["include_unrelated"] is False
    assert [kind for kind, _ in preview["records"]] == [ENTITY_TYPE_INCIDENT]


def test_preview_yes_only_omits_unrelated_counts() -> None:
    manager = _sample_manager()
    preview = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes", max_fetch=5).preview(sample_limit=5)
    assert preview["include_related"] is True
    assert preview["include_unrelated"] is False
    assert preview["related_alert_count"] == 2
    assert preview["unrelated_alert_count"] == 0
    assert preview["total_alert_count"] == 2
    ids = [record.get("id") for _, record in preview["records"]]
    assert "alert-3" not in ids


def test_preview_related_count_uses_incident_nested_alerts() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Campaign",
            "alertsCount": 2,
            "alerts": [{"alertId": "alert-1"}, {"alertId": "alert-2"}],
        }
    ]
    manager.alerts = [{"id": "alert-3", "name": "Noise"}]
    preview = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes", max_fetch=5).preview(sample_limit=5)
    assert preview["related_alert_count"] == 2
    assert preview["unrelated_alert_count"] == 0


def test_already_ingested_incident_skips_timeline_and_id_lookup() -> None:
    manager = _sample_manager()
    first = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    assert manager.timeline_calls == ["inc-1"]
    manager.alert_calls.clear()
    manager.timeline_calls.clear()
    second = _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run(checkpoint=first["checkpoint"])
    assert second["fetched"] == 0
    assert manager.timeline_calls == []
    assert not any(call.get("alertIds") or call.get("vegaAlertIds") for call in manager.alert_calls)


def test_uuid_stubs_are_not_retried_as_vega_alert_ids() -> None:
    uuid = "019e1b27-5119-7822-bde3-344b13e481cf"
    manager = FakeManager()
    manager.incidents = [{"id": "inc-1", "name": "Campaign", "alerts": [{"alertId": uuid, "name": "Phish"}]}]
    manager.alerts = [{"id": uuid, "name": "Phish"}]
    _pipeline(manager, entities="Alerts,Incidents", has_related="Yes").run()
    assert not any(call.get("vegaAlertIds") for call in manager.alert_calls)
    assert any(uuid in (call.get("alertIds") or []) for call in manager.alert_calls)


def _metadata_uuid(index: int) -> str:
    return f"019e1b27-5119-7822-bde3-{index:012d}"


def test_vega_alerts_stays_get_incidents_stub_when_metadata_disabled() -> None:
    uuid = _metadata_uuid(1)
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Campaign",
            "createdAt": "2026-01-01T00:00:00Z",
            "alerts": [
                {
                    "alertId": uuid,
                    "name": "Phish",
                    "createdAt": "2024-01-15T09:30:00Z",
                    "severity": "HIGH",
                }
            ],
        }
    ]
    manager.alerts = [
        {
            "id": uuid,
            "name": "Phish",
            "detectionId": "det-1",
            "detectionQuery": "index=proxy",
        }
    ]
    summary = _pipeline(manager, entities="Incidents", has_related="No").run()
    incident = summary["records"][0][1]
    assert incident["vega_alerts"] == [
        {
            "alertId": uuid,
            "name": "Phish",
            "createdAt": "2024-01-15T09:30:00Z",
        }
    ]
    assert incident["alerts"][0]["severity"] == "HIGH"
    assert manager.alert_calls == []


def test_vega_alerts_loads_full_metadata_when_enabled() -> None:
    uuid = _metadata_uuid(2)
    missing = _metadata_uuid(3)
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Campaign",
            "createdAt": "2026-01-01T00:00:00Z",
            "alerts": [
                {"alertId": uuid, "name": "Phish", "createdAt": "2024-01-15T09:30:00Z"},
                {"alertId": missing, "name": "Gone", "createdAt": "2024-01-16T09:30:00Z"},
            ],
        }
    ]
    manager.alerts = [
        {
            "id": uuid,
            "name": "Phish",
            "detectionId": "det-1",
            "detectionSource": "splunk",
            "detectionDescription": "proxy beacon",
            "detectionQuery": "index=proxy",
            "status": "OPEN",
            "verdict": "MALICIOUS",
        }
    ]
    summary = _pipeline(
        manager,
        entities="Incidents",
        has_related="No",
        fetch_related_alert_metadata=True,
    ).run()
    incident = summary["records"][0][1]
    assert len(summary["records"]) == 1
    assert incident["alerts"][0] == {
        "alertId": uuid,
        "name": "Phish",
        "createdAt": "2024-01-15T09:30:00Z",
    }
    full = incident["vega_alerts"][0]
    assert full["detectionId"] == "det-1"
    assert full["detectionQuery"] == "index=proxy"
    assert full["verdict"] == "MALICIOUS"
    assert incident["vega_alerts"][1] == {
        "alertId": missing,
        "name": "Gone",
        "createdAt": "2024-01-16T09:30:00Z",
    }
    assert len(manager.alert_calls) == 1
    call = manager.alert_calls[0]
    assert call["alertIds"] == [uuid, missing]
    assert call["from"]
    assert "alertSeverities" not in call
    assert manager.alert_fetch_limits == [2]


def test_vega_alerts_sends_human_ids_as_vega_alert_ids() -> None:
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Campaign",
            "createdAt": "2026-01-01T00:00:00Z",
            "alerts": [{"alertId": "VEGA-9", "name": "Phish"}],
        }
    ]
    manager.alerts = [{"id": "ignored", "vegaAlertId": "VEGA-9", "detectionId": "det-9"}]
    summary = _pipeline(manager, entities="Incidents", fetch_related_alert_metadata=True).run()
    assert manager.alert_calls[0]["vegaAlertIds"] == ["VEGA-9"]
    assert "alertIds" not in manager.alert_calls[0]
    assert summary["records"][0][1]["vega_alerts"][0]["detectionId"] == "det-9"


def test_vega_alerts_batches_one_thousand_uuids_per_request() -> None:
    from core.constants import ALERT_METADATA_ID_BATCH

    ids = [_metadata_uuid(index) for index in range(ALERT_METADATA_ID_BATCH + 1)]
    manager = FakeManager()
    manager.incidents = [
        {
            "id": "inc-1",
            "name": "Campaign",
            "createdAt": "2026-01-01T00:00:00Z",
            "alerts": [{"alertId": item} for item in ids],
        }
    ]
    summary = _pipeline(manager, entities="Incidents", fetch_related_alert_metadata=True).run()
    assert [len(call["alertIds"]) for call in manager.alert_calls] == [
        ALERT_METADATA_ID_BATCH,
        1,
    ]
    assert manager.alert_fetch_limits == [ALERT_METADATA_ID_BATCH, 1]
    assert len(summary["records"][0][1]["vega_alerts"]) == ALERT_METADATA_ID_BATCH + 1
