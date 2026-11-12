"""Tests for Vega SOAR case/alert/event hierarchy mapping."""

from __future__ import annotations

import json

from core.alert_event_mapping import build_vega_alert_event_dict
from core.constants import (
    ENTITY_TYPE_ALERT,
    ENTITY_TYPE_INCIDENT,
    GET_ALERTS_QUERY,
    GET_INCIDENTS_QUERY,
    SOAR_ALERT_TYPE_ALERT,
    SOAR_ALERT_TYPE_INCIDENT,
    UPDATE_INCIDENTS_MUTATION,
    UPDATE_INCIDENTS_STATUS_MUTATION,
)
from core.mapping import (
    alert_grouping_id,
    build_event_dict,
    case_display_name,
    collect_label_tags,
    incident_alert_ids,
    incident_case_title,
    incident_grouping_id,
    is_graphql_alert_id,
    merge_related_alert,
    pending_case_tags,
    record_id,
    record_label_tags,
    related_incident_ref,
    set_soar_meta,
    soar_meta,
    stub_to_alert,
    tags_from_events,
)
from core.Remediator import extract_sync_targets


def test_case_display_name_uses_entity_display_id_and_name() -> None:
    assert case_display_name({"vegaAlertId": "VALERT-1", "name": "Phish"}, ENTITY_TYPE_ALERT).startswith(
        "Vega Alert - VALERT-1 - Phish"
    )
    assert case_display_name(
        {"vegaUniqueIncidentId": "VINC-1", "name": "Campaign"},
        ENTITY_TYPE_INCIDENT,
    ).startswith("Vega Incident - VINC-1 - Campaign")
    incident = {"vegaUniqueIncidentId": "VINC-1", "name": "Campaign"}
    assert incident_case_title(incident).startswith("Vega Incident - VINC-1 - Campaign")
    assert "(related alerts)" not in incident_case_title(incident)
    related_title = incident_case_title(incident, related=True)
    assert related_title.endswith("(related alerts)")
    assert incident_case_title(incident, related=True) == related_title
    uuid = "019e1b27-5119-7822-bde3-344b13e481cf"
    assert case_display_name(
        {"id": uuid, "alertId": uuid, "vegaAlertId": "VALERT-9", "name": "Persist"},
        ENTITY_TYPE_ALERT,
    ).startswith("Vega Alert - VALERT-9 - Persist")
    uuid_only = case_display_name({"id": uuid, "alertId": uuid, "name": "Persist"}, ENTITY_TYPE_ALERT)
    assert uuid not in uuid_only
    assert uuid_only.startswith("Vega Alert - Persist")


def test_record_id_reads_nested_alert_stub() -> None:
    assert record_id({"alertId": "abc"}, ENTITY_TYPE_ALERT) == "abc"
    assert stub_to_alert({"alertId": "abc", "name": "x"})["id"] == "abc"


def test_label_tags_are_unique_by_name() -> None:
    tags = record_label_tags({
        "labels": [
            {"name": "malware"},
            {"name": "Malware"},
            {"name": "apt"},
            "apt",
            {"name": ""},
            {"labelName": "c2"},
            {"name": "x"},
        ]
    })
    assert tags == ["malware", "apt", "c2"]


def test_collect_label_tags_unions_incident_and_alert_labels() -> None:
    tags = collect_label_tags(
        {"labels": [{"name": "malware"}, {"name": "campaign"}]},
        {"labels": [{"name": "Phish"}, "malware"]},
        {"labels": [{"name": "c2"}]},
        {},
    )
    assert tags == ["malware", "campaign", "Phish", "c2"]


def test_graphql_queries_request_label_name_and_color_only() -> None:
    assert "labels { name color }" in GET_ALERTS_QUERY
    assert "labels { id" not in GET_ALERTS_QUERY
    assert "categoryId" not in GET_ALERTS_QUERY
    assert "usageCount" not in GET_ALERTS_QUERY
    assert "labels { id categoryId name color usageCount }" in GET_INCIDENTS_QUERY
    assert "investigationStatus" in GET_INCIDENTS_QUERY
    assert "userStatus" in GET_INCIDENTS_QUERY
    assert "$statuses:" not in GET_INCIDENTS_QUERY
    assert "statuses: $statuses" not in GET_INCIDENTS_QUERY
    assert "sortBy" not in GET_ALERTS_QUERY
    assert "originType" not in GET_ALERTS_QUERY
    assert "escalation" in GET_ALERTS_QUERY
    assert "alerts { alertId name createdAt }" in GET_INCIDENTS_QUERY
    assert "alerts { alertId vegaAlertId" not in GET_INCIDENTS_QUERY
    assert "alerts { alertId name createdAt labels" not in GET_INCIDENTS_QUERY
    for query in (UPDATE_INCIDENTS_MUTATION, UPDATE_INCIDENTS_STATUS_MUTATION):
        assert "userStatus" in query
        assert "investigationStatus" in query
        assert "incidentId status" not in query
        assert "\n      status\n" not in query


def test_stub_to_alert_keeps_nested_labels() -> None:
    stub = stub_to_alert({
        "alertId": "abc",
        "name": "x",
        "labels": [{"name": "incident-33 related alert", "color": "BLUE"}],
    })
    assert stub["id"] == "abc"
    assert stub["labels"] == [{"name": "incident-33 related alert", "color": "BLUE"}]


def test_merge_related_alert_uses_stub_labels_when_full_has_none() -> None:
    stub = {
        "alertId": "alert-1",
        "vegaAlertId": "VEGA-2418",
        "labels": [{"name": "incident-33 related alert"}],
    }
    full = {"id": "alert-1", "name": "Phish", "labels": []}
    merged = merge_related_alert(stub, full)
    assert merged["labels"] == [{"name": "incident-33 related alert"}]
    assert merged["vegaAlertId"] == "VEGA-2418"
    assert merge_related_alert(stub, None)["labels"] == [{"name": "incident-33 related alert"}]


def test_alert_event_maps_label_name_and_color_only() -> None:
    event = build_event_dict(
        {
            "id": "alert-1",
            "name": "Phish",
            "labels": [
                {
                    "id": "lbl-1",
                    "categoryId": "cat-1",
                    "name": "phish",
                    "color": "#ff0000",
                    "usageCount": 9,
                },
                {"name": "malware"},
            ],
        },
        ENTITY_TYPE_ALERT,
        1,
        1,
    )
    labels = json.loads(event["labels"])
    assert labels == [{"name": "phish", "color": "#ff0000"}, {"name": "malware"}]
    assert event["vega_label_names"] == "phish,malware"
    details = json.loads(event["details"])
    assert details["labels"] == labels
    assert "categoryId" not in event["labels"]
    assert "usageCount" not in event["labels"]
    assert "categoryId" not in event["details"]
    assert "usageCount" not in event["details"]


def test_incident_event_maps_label_name_and_color_only() -> None:
    event = build_event_dict(
        {
            "id": "inc-1",
            "name": "Campaign",
            "labels": [
                {
                    "id": "lbl-2",
                    "categoryId": "cat-2",
                    "name": "campaign",
                    "color": "#00aa00",
                    "usageCount": 3,
                }
            ],
        },
        ENTITY_TYPE_INCIDENT,
        1,
        1,
    )
    labels = json.loads(event["labels"])
    assert labels == [{"name": "campaign", "color": "#00aa00"}]
    details = json.loads(event["details"])
    assert details["labels"] == labels


def test_alert_event_keeps_empty_labels_list() -> None:
    event = build_event_dict(
        {"id": "alert-1", "name": "Phish", "labels": []},
        ENTITY_TYPE_ALERT,
        1,
        1,
    )
    assert json.loads(event["labels"]) == []
    assert "vega_label_names" not in event
    assert json.loads(event["details"])["labels"] == []


def test_alert_event_keeps_labels_when_missing() -> None:
    event = build_event_dict(
        {"id": "alert-1", "name": "Phish"},
        ENTITY_TYPE_ALERT,
        1,
        1,
    )
    assert json.loads(event["labels"]) == []
    assert json.loads(event["details"])["labels"] == []


def test_incident_event_keeps_empty_labels_list() -> None:
    event = build_event_dict(
        {"id": "inc-1", "name": "Campaign", "labels": []},
        ENTITY_TYPE_INCIDENT,
        1,
        1,
    )
    assert json.loads(event["labels"]) == []
    assert json.loads(event["details"])["labels"] == []


def test_related_alert_event_does_not_copy_incident_labels() -> None:
    event = build_event_dict(
        set_soar_meta(
            {"id": "alert-1", "vegaAlertId": "VALERT-1", "name": "Phish", "labels": []},
            incident_id="inc-1",
            incident_label_tags=["campaign", "IT"],
            is_incident_case=True,
        ),
        ENTITY_TYPE_ALERT,
        1,
        1,
    )
    assert json.loads(event["labels"]) == []
    assert "vega_label_names" not in event
    assert event["vega_incident_label_names"] == "campaign,IT"


def test_tags_from_events_reads_incident_label_names_on_overflow() -> None:
    tags = tags_from_events([
        {
            "labels": "[]",
            "vega_incident_label_names": "campaign,IT",
        },
        {
            "labels": json.dumps([{"name": "beacon", "color": "BLUE"}]),
        },
    ])
    assert tags == ["campaign", "IT", "beacon"]


def test_tags_from_events_unions_incident_and_related_alert_labels() -> None:
    tags = tags_from_events([
        {
            "labels": json.dumps([
                {"name": "incident", "color": "BLUE"},
                {"name": "IT", "color": "BLUE"},
            ]),
            "vega_label_names": "incident,IT",
        },
        {
            "labels": json.dumps([{"name": "incident-33 related alert", "color": "BLUE"}]),
            "vega_label_names": "incident-33 related alert",
        },
        {"labels": "[]"},
    ])
    assert tags == ["incident", "IT", "incident-33 related alert"]


def test_tags_from_events_reads_label_json_and_csv() -> None:
    tags = tags_from_events([
        {"labels": [{"name": "malware"}]},
        {"vega_label_names": "phish, malware"},
        {"vega_label_names": "c2"},
    ])
    assert tags == ["malware", "phish", "c2"]


def test_tags_from_events_reads_nested_soar_event_shapes() -> None:
    class SecurityEvent:
        def __init__(self) -> None:
            self.additional_properties = {"details": json.dumps({"labels": [{"name": "campaign", "color": "#00aa00"}]})}

    tags = tags_from_events([
        {"additional_properties": {"labels": json.dumps([{"name": "phish", "color": "#ff0000"}])}},
        SecurityEvent(),
        {"vega_label_names": "noise"},
    ])
    assert tags == ["phish", "campaign", "noise"]


def test_record_label_tags_parses_json_string() -> None:
    tags = record_label_tags({"labels": json.dumps([{"name": "malware"}, {"name": "c2"}])})
    assert tags == ["malware", "c2"]


def test_pending_case_tags_skips_existing_and_duplicates() -> None:
    assert pending_case_tags(
        ["malware", "Malware", "phish", "c2", "x"],
        existing=["PHISH"],
    ) == ["malware", "c2"]


def test_related_incident_ref() -> None:
    assert related_incident_ref({"relatedIncidents": [{"incidentId": "inc-1", "name": "Campaign"}]}) == (
        "inc-1",
        "Campaign",
    )
    assert related_incident_ref({}) == ("", "")


def test_grouping_ids() -> None:
    assert incident_grouping_id("inc-1") == "Vega:incident:inc-1"
    assert incident_grouping_id("inc-1", related=False) == "Vega:incident:inc-1"
    assert incident_grouping_id("inc-1", related=True) == "Vega:incident:inc-1:related"
    assert incident_grouping_id("inc-1", batch=1) == "Vega:incident:inc-1:related:cluster:1"
    assert incident_grouping_id("inc-1", batch=2) == "Vega:incident:inc-1:related:cluster:2"
    assert incident_case_title({"name": "Campaign"}, batch=2).endswith("(cluster 2)")
    assert alert_grouping_id("a-1") == "Vega:alert:a-1"
    assert is_graphql_alert_id("019e1b27-5119-7822-bde3-344b13e481cf")
    assert not is_graphql_alert_id("VEGA-3219")
    assert not is_graphql_alert_id("alert-1")


def test_incident_alert_ids() -> None:
    incident = {
        "alerts": [
            {"alertId": "alert-1", "name": "Phish"},
            {"alertId": "alert-1"},
            {"alertId": "alert-2"},
        ]
    }
    assert incident_alert_ids(incident) == ["alert-1", "alert-2"]


def test_summary_event_carries_incident_id_and_alert_type() -> None:
    record = set_soar_meta(
        {"id": "alert-1", "vegaAlertId": "VALERT-1", "name": "Phish"},
        soar_alert_type=SOAR_ALERT_TYPE_INCIDENT,
        incident_id="inc-1",
        incident_display_id="VINC-1",
    )
    event = build_event_dict(record, ENTITY_TYPE_ALERT, 1, 1)
    assert event["event_type"] == SOAR_ALERT_TYPE_INCIDENT
    assert event["vega_incident_id"] == "inc-1"
    assert event["vega_unique_incident_id"] == "VINC-1"
    assert "_soar_meta" not in event["details"]


_EMPTY_API_KEYS = (
    "status",
    "user_status",
    "investigation_status",
    "verdict",
    "verdict_reasoning",
    "description",
    "source_url",
    "created_at",
    "updated_at",
    "vega_incident_id",
    "vega_unique_incident_id",
    "comments",
    "skills",
    "recommended_actions",
    "investigation_plan",
    "timeline",
    "observables",
    "assets",
    "vega_entities",
    "vega_alert_events_count",
    "vega_comments",
    "vega_labels",
    "vega_skills",
    "vega_recommended_actions",
    "vega_investigation_plan",
    "vega_timeline",
    "vega_observables",
    "vega_assets",
    "vega_recommended_action_keys",
    "vega_reset_password_user",
)


def test_alert_event_omits_missing_api_fields() -> None:
    event = build_event_dict(
        {"id": "alert-1", "vegaAlertId": "VALERT-1", "name": "Phish"},
        ENTITY_TYPE_ALERT,
        1,
        1,
    )
    assert event["vega_alert_id"] == "VALERT-1"
    assert json.loads(event["labels"]) == []
    for key in _EMPTY_API_KEYS:
        assert key not in event, key


def test_alert_event_maps_get_alerts_fields() -> None:
    event = build_event_dict(
        {
            "id": "alert-1",
            "vegaAlertId": "VALERT-1",
            "name": "Phish",
            "description": "Click",
            "severity": "HIGH",
            "status": "OPEN",
            "detectionId": "det-1",
            "dataSources": ["splunk"],
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
            "verdict": "MALICIOUS",
            "verdictReasoning": "because",
            "eventCount": 3,
            "href": "https://vega.example/alerts/1",
            "comments": [{"text": "hi"}],
            "labels": [{"name": "phish"}],
            "relatedIncidents": [{"incidentId": "inc-1", "name": "Campaign"}],
        },
        ENTITY_TYPE_ALERT,
        1,
        1,
    )
    assert event["detection_id"] == "det-1"
    assert event["event_count"] == "3"
    assert event["verdict"] == "MALICIOUS"
    assert event["source_url"] == "https://vega.example/alerts/1"
    assert "recommended_actions" not in event
    assert "investigation_plan" not in event
    assert "observables" not in event
    assert "assets" not in event
    assert "vega_entities" not in event


def test_incident_event_maps_get_incidents_fields() -> None:
    event = build_event_dict(
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "incidentSummary": "summary",
            "incidentFindings": "findings",
            "investigationStatus": "NEW",
            "userStatus": "OPEN",
            "severity": "HIGH",
            "recommendedActions": [{"name": "block"}],
            "investigationPlan": [{"stepName": "scope"}],
            "observables": ["1.1.1.1"],
            "assets": ["host-1"],
            "alertsCount": 2,
            "createdBy": "analyst",
            "link": "https://vega.example/incidents/1",
            "timeline": [{"summary": "opened"}],
        },
        ENTITY_TYPE_INCIDENT,
        1,
        1,
    )
    assert event["vega_unique_incident_id"] == "VINC-1"
    assert event["description"] == "summary"
    assert event["incident_findings"] == "findings"
    assert event["created_by"] == "analyst"
    assert event["investigation_status"] == "NEW"
    assert event["user_status"] == "OPEN"
    assert "status" not in event
    assert event["source_url"] == "https://vega.example/incidents/1"
    assert "vega_alert_id" not in event
    assert "detection_id" not in event
    assert "event_count" not in event
    assert "recommended_actions" in event
    assert "investigation_plan" in event
    assert "observables" in event
    assert "assets" in event
    assert "timeline" in event
    assert "vega_entities" not in event
    for key in ("vega_recommended_actions", "vega_investigation_plan", "vega_observables"):
        assert key not in event, key
    assert "vega_recommended_action_keys" not in event
    assert "vega_reset_password_user" not in event
    assert event["vega_alerts"] == "[]"
    assert event["vega_related_alert_ids"] == "[]"
    assert "alerts" not in event


def test_incident_event_maps_get_incidents_alert_stubs_onto_vega_alerts() -> None:
    event = build_event_dict(
        {
            "id": "inc-1",
            "name": "Campaign",
            "alerts": [
                {
                    "alertId": "019e1b27-5119-7822-bde3-344b13e481cf",
                    "name": "Phish",
                    "createdAt": "2024-01-15T09:30:00Z",
                }
            ],
        },
        ENTITY_TYPE_INCIDENT,
        1,
        1,
    )
    assert "alerts" not in event
    assert json.loads(event["vega_alerts"]) == [
        {
            "alertId": "019e1b27-5119-7822-bde3-344b13e481cf",
            "name": "Phish",
            "createdAt": "2024-01-15T09:30:00Z",
        }
    ]
    assert event["vega_related_alert_ids"] == "019e1b27-5119-7822-bde3-344b13e481cf"


def test_incident_event_maps_vega_alerts_without_copying_into_details() -> None:
    event = build_event_dict(
        {
            "id": "inc-1",
            "name": "Campaign",
            "alerts": [{"alertId": "stub-1", "name": "Phish"}],
            "vega_alerts": [
                {
                    "id": "019e1b27-5119-7822-bde3-344b13e481cf",
                    "detectionId": "det-1",
                    "detectionQuery": "index=proxy",
                    "verdict": "MALICIOUS",
                }
            ],
        },
        ENTITY_TYPE_INCIDENT,
        1,
        1,
    )
    parsed = json.loads(event["vega_alerts"])
    assert parsed[0]["detectionId"] == "det-1"
    assert parsed[0]["detectionQuery"] == "index=proxy"
    assert event["vega_related_alert_ids"] == "019e1b27-5119-7822-bde3-344b13e481cf"
    assert "alerts" not in event
    details = json.loads(event["details"])
    assert "vega_alerts" not in details
    assert details["alerts"] == [{"alertId": "stub-1", "name": "Phish"}]


def test_incident_event_extracts_okta_reset_user_from_recommended_actions() -> None:
    event = build_event_dict(
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "recommendedActions": [
                {
                    "name": "Block Exfiltration Destination IP",
                    "actionKey": "block_ip",
                    "targetParams": {"ip": "178.128.212.209"},
                },
                {
                    "name": "Revoke Compromised User Sessions",
                    "actionKey": "revoke_user_sessions",
                    "targetParams": {"user_id": "alakesh.kothar@metronlabs.com"},
                },
                {
                    "name": "Reset Compromised User Password",
                    "actionKey": "reset_user_password",
                    "targetParams": {"user_id": "alakesh.kothar@metronlabs.com"},
                },
            ],
        },
        ENTITY_TYPE_INCIDENT,
        1,
        1,
    )
    assert event["vega_recommended_action_keys"] == ("block_ip,revoke_user_sessions,reset_user_password")
    assert event["vega_reset_password_user"] == "alakesh.kothar@metronlabs.com"
    assert event["user"] == "alakesh.kothar@metronlabs.com"
    assert "reset_user_password" in event["recommended_actions"]


def test_reset_password_users_from_payload_reads_recommended_actions_json() -> None:
    from core.mapping import reset_password_users_from_payload

    users = reset_password_users_from_payload({
        "recommended_actions": json.dumps([
            {
                "actionKey": "reset_user_password",
                "targetParams": {"user_id": "alakesh.kothar@metronlabs.com"},
            }
        ])
    })
    assert users == ["alakesh.kothar@metronlabs.com"]


def test_child_events_stay_scoped_to_parent_alert() -> None:
    parent = set_soar_meta(
        {
            "id": "alert-1",
            "vegaAlertId": "VALERT-1",
            "labels": [{"name": "phish", "color": "#ff0000"}],
        },
        incident_id="inc-1",
        incident_label_tags=["campaign"],
    )
    event = build_vega_alert_event_dict(parent, {"name": "login", "src_ip": "1.1.1.1"}, 1, 1, 0)
    assert event["product_log_id"] == "alert-1:event:0"
    assert event["vega_id"] == "alert-1"
    assert event["vega_incident_id"] == "inc-1"
    assert event["vega_entity_type"] == "Alert Event"
    assert json.loads(event["labels"]) == [{"name": "phish", "color": "#ff0000"}]
    assert event["vega_label_names"] == "phish"
    assert event["vega_incident_label_names"] == "campaign"


def test_alert_event_payload_maps_dynamic_api_fields() -> None:
    event = build_vega_alert_event_dict(
        {"id": "alert-1", "vegaAlertId": "VALERT-1"},
        {
            "name": "login",
            "src_ip": "1.1.1.1",
            "custom_field": "abc",
            "empty_field": "",
            "null_field": None,
            "empty_list": [],
            "nested": {"user": "bob", "host": "ws1"},
        },
        1,
        1,
        0,
    )
    assert event["src_ip"] == "1.1.1.1"
    assert event["custom_field"] == "abc"
    assert event["user"] == "bob"
    assert event["host"] == "ws1"
    assert event["ip"] == "1.1.1.1"
    assert event["vega_alert_id"] == "VALERT-1"
    assert "empty_field" not in event
    assert "null_field" not in event
    assert "empty_list" not in event
    assert "vega_incident_id" not in event
    assert "SourceGroupingIdentifier" not in event


def test_child_event_overwrites_invalid_payload_times() -> None:
    event = build_vega_alert_event_dict(
        {"id": "alert-1", "vegaAlertId": "VALERT-1"},
        {
            "name": "login",
            "StartTime": "invalid",
            "starttime": "0",
            "Time": "not-a-date",
            "_time": "0",
            "timestamp": "none",
        },
        1_700_000_000_000,
        1_700_000_000_000,
        0,
    )
    assert event["StartTime"] == 1_700_000_000_000
    assert event["EndTime"] == 1_700_000_000_000
    assert "metadata" not in event
    assert "metadata.event_timestamp" not in event
    assert "udm_event_timestamp" not in event
    assert "event_time_rfc3339" not in event
    assert "start_time" not in event
    assert "end_time" not in event
    assert "starttime" not in event
    assert "Time" not in event
    assert "_time" not in event
    assert "timestamp" not in event
    assert "event_timestamp" not in event


def test_parent_event_keeps_single_start_and_end_time() -> None:
    event = build_event_dict(
        {"id": "inc-1", "vegaUniqueIncidentId": "INC-1", "name": "Campaign"},
        ENTITY_TYPE_INCIDENT,
        1_700_000_000_000,
        1_700_000_000_000,
    )
    assert event["StartTime"] == 1_700_000_000_000
    assert event["EndTime"] == 1_700_000_000_000
    assert "metadata" not in event
    assert "metadata.event_timestamp" not in event
    assert "udm_event_timestamp" not in event
    assert "event_time_rfc3339" not in event
    assert "start_time" not in event
    assert "end_time" not in event
    assert "time" not in event
    assert "timestamp" not in event
    assert "event_timestamp" not in event


def test_extract_sync_targets_incident_case_ignores_related_alerts() -> None:
    targets = extract_sync_targets({
        "events": [
            {"vega_entity_type": "Incident", "vega_id": "inc-1"},
            {
                "vega_entity_type": "Alert",
                "vega_id": "alert-1",
                "vega_incident_id": "inc-1",
            },
        ]
    })
    assert targets["mode"] == "incident"
    assert targets["incident_ids"] == ["inc-1"]
    assert targets["alert_ids"] == []


def test_extract_sync_targets_related_batch_does_not_close_incident() -> None:
    targets = extract_sync_targets({
        "events": [
            {
                "vega_entity_type": "Alert",
                "vega_id": "alert-1",
                "vega_incident_id": "inc-1",
            },
            {
                "vega_entity_type": "Alert Event",
                "vega_id": "alert-1",
                "product_log_id": "alert-1:event:0",
                "vega_incident_id": "inc-1",
            },
        ]
    })
    assert targets["mode"] == "alerts"
    assert targets["incident_ids"] == []
    assert targets["alert_ids"] == ["alert-1"]


def test_extract_sync_targets_unrelated_alert() -> None:
    targets = extract_sync_targets({"events": [{"vega_entity_type": "Alert", "vega_id": "alert-3"}]})
    assert targets["mode"] == "alerts"
    assert targets["incident_ids"] == []
    assert targets["alert_ids"] == ["alert-3"]


def test_extract_sync_targets_camel_case_prefers_uuid_over_vinc() -> None:
    uuid = "019eea19-551b-7b19-8582-faff640969ff"
    targets = extract_sync_targets({
        "title": "Vega Incident - VINC-1 - phishing",
        "securityEvents": [
            {
                "vegaEntityType": "Incident",
                "vegaUniqueIncidentId": "VINC-1",
                "eventClassId": uuid,
            }
        ],
    })
    assert targets["mode"] == "incident"
    assert targets["incident_ids"] == [uuid]
    assert targets["alert_ids"] == []


def test_extract_sync_targets_ticket_id_when_events_dropped() -> None:
    uuid = "019eea19-551b-7b19-8582-faff640969ff"
    targets = extract_sync_targets({
        "title": "Vega Incident - VINC-1 - phishing",
        "cyberAlerts": [{"ticketId": f"Vega:{uuid}"}],
    })
    assert targets["mode"] == "incident"
    assert targets["incident_ids"] == [uuid]


def test_extract_sync_targets_related_title_does_not_close_incident() -> None:
    uuid = "019eea19-551b-7b19-8582-faff640969ff"
    targets = extract_sync_targets({
        "title": "Vega Incident - VINC-1 - phishing (related alerts)",
        "events": [
            {
                "vegaEntityType": "Alert",
                "vegaId": "alert-1",
                "vegaIncidentId": uuid,
            }
        ],
    })
    assert targets["mode"] == "alerts"
    assert targets["alert_ids"] == ["alert-1"]
    assert targets["incident_ids"] == []


def test_extract_sync_targets_legacy_batch_title_does_not_close_incident() -> None:
    uuid = "019eea19-551b-7b19-8582-faff640969ff"
    targets = extract_sync_targets({
        "title": "Vega Incident - VINC-1 - phishing (cluster 1)",
        "cyberAlerts": [{"ticketId": f"Vega:{uuid}"}],
    })
    assert targets["mode"] == "alerts"
    assert targets["incident_ids"] == []
    assert targets["alert_ids"] == [uuid]


def test_soar_meta_round_trip() -> None:
    record = set_soar_meta({"id": "1"}, soar_alert_type=SOAR_ALERT_TYPE_ALERT)
    assert soar_meta(record)["soar_alert_type"] == SOAR_ALERT_TYPE_ALERT
