"""Tests for AlertInfo packaging fields used by SOAR search and grouping."""

from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace

from core.constants import ENTITY_TYPE_ALERT, ENTITY_TYPE_INCIDENT
from core.mapping import set_soar_meta


class FakeAlertInfo:
    def __init__(self) -> None:
        self.events: list = []
        self.extensions: dict = {}
        self.case_tags = None
        self.tags = None
        self.rule_generator = ""
        self.device_product = ""
        self.source_grouping_identifier = ""
        self.name = ""
        self.display_id = ""
        self.ticket_id = ""
        self.device_vendor = ""
        self.device_event_class_id = ""
        self.environment = ""
        self.description = ""
        self.start_time = 0
        self.end_time = 0
        self.Severity = ""
        self.priority = 0


def _install_fake_sdk() -> None:
    soar_sdk = ModuleType("soar_sdk")
    data_model = ModuleType("soar_sdk.SiemplifyConnectorsDataModel")
    utils = ModuleType("soar_sdk.SiemplifyUtils")
    data_model.AlertInfo = FakeAlertInfo
    utils.unix_now = lambda: 1
    sys.modules["soar_sdk"] = soar_sdk
    sys.modules["soar_sdk.SiemplifyConnectorsDataModel"] = data_model
    sys.modules["soar_sdk.SiemplifyUtils"] = utils


def test_packager_related_alerts_share_case_title_not_alert_type() -> None:
    case_title = "Vega Incident - VINC-1 - Campaign"
    incident = set_soar_meta(
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "createdAt": "2026-07-28T11:22:43Z",
            "labels": [
                {
                    "id": "lbl-1",
                    "categoryId": "cat-1",
                    "name": "campaign",
                    "color": "#00aa00",
                    "usageCount": 2,
                }
            ],
        },
        grouping_id="Vega:incident:inc-1",
        case_tags=["malware"],
        case_title=case_title,
        grouping_time="2026-07-28T11:22:43Z",
        incident_id="inc-1",
        is_incident_case=True,
    )
    related = set_soar_meta(
        {
            "id": "alert-1",
            "vegaAlertId": "VALERT-1",
            "name": "Phish",
            "createdAt": "2026-04-05T01:18:35Z",
            "labels": [{"name": "phish", "color": "#ff0000"}],
            "alert_events": [{"name": "login"}],
        },
        grouping_id="Vega:incident:inc-1:related",
        case_title=f"{case_title} (related alerts)",
        grouping_time="2026-07-28T11:22:43Z",
        incident_id="inc-1",
        is_incident_case=True,
    )
    unrelated = set_soar_meta(
        {
            "id": "alert-3",
            "vegaAlertId": "VALERT-3",
            "name": "Noise",
            "labels": [{"name": "noise", "color": "#888888"}],
        },
        grouping_id="Vega:alert:alert-3",
        case_tags=[],
        is_incident_case=False,
    )
    siemplify = SimpleNamespace(context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default")))
    _install_fake_sdk()
    from core.AlertPackager import create_alerts

    packages = create_alerts(
        [
            (ENTITY_TYPE_INCIDENT, incident),
            (ENTITY_TYPE_ALERT, related),
            (ENTITY_TYPE_ALERT, unrelated),
        ],
        siemplify,
    )
    assert len(packages) == 3
    incident_alert, related_alert, standalone = packages
    assert incident_alert.rule_generator == case_title
    assert related_alert.rule_generator == f"{case_title} (related alerts)"
    assert incident_alert.name.startswith("Vega Incident - VINC-1 - Campaign")
    assert related_alert.name.startswith("Vega Alert - VALERT-1 - Phish")
    assert "Vega Alert" not in incident_alert.rule_generator
    assert "Vega Incident" != incident_alert.rule_generator
    assert standalone.rule_generator.startswith("Vega Alert - VALERT-3 - Noise")
    assert standalone.name.startswith("Vega Alert - VALERT-3 - Noise")
    assert incident_alert.device_product == "Vega"
    assert related_alert.device_product == "Vega"
    assert standalone.device_product == "Vega"
    assert incident_alert.source_grouping_identifier == "Vega:incident:inc-1"
    assert related_alert.source_grouping_identifier == "Vega:incident:inc-1:related"
    assert standalone.source_grouping_identifier == "Vega:alert:alert-3"
    assert incident_alert.start_time == incident_alert.events[0]["StartTime"]
    assert incident_alert.end_time == incident_alert.events[0]["EndTime"]
    assert related_alert.start_time == related_alert.events[0]["StartTime"]
    assert related_alert.end_time == related_alert.events[0]["EndTime"]
    assert related_alert.start_time != incident_alert.start_time
    assert related_alert.events[1]["StartTime"] == related_alert.start_time
    assert related_alert.events[1]["EndTime"] == related_alert.end_time
    assert incident_alert.case_tags is None
    assert incident_alert.tags is None
    assert "tags" not in incident_alert.extensions
    assert incident_alert.extensions["vega_id"] == "inc-1"
    assert incident_alert.extensions["vega_entity_type"] == ENTITY_TYPE_INCIDENT
    assert related_alert.extensions["vega_id"] == "alert-1"
    assert "tags" not in incident_alert.events[0]
    assert getattr(related_alert, "tags", None) in (None, [], "")
    assert standalone.case_tags is None
    assert standalone.tags is None
    assert len(incident_alert.events) == 1
    assert incident_alert.events[0]["name"].startswith("Vega Incident - VINC-1 - Campaign")
    assert len(related_alert.events) == 2
    assert related_alert.events[0]["name"].startswith("Vega Alert - VALERT-1 - Phish")
    assert related_alert.events[1]["name"] == "login"
    assert "SourceGroupingIdentifier" not in related_alert.extensions
    assert "sourceGroupIdentifier" not in related_alert.events[0]
    assert "SourceGroupingIdentifier" not in related_alert.events[0]
    assert json.loads(incident_alert.events[0]["labels"]) == [{"name": "campaign", "color": "#00aa00"}]
    assert "categoryId" not in incident_alert.events[0]["labels"]
    assert json.loads(related_alert.events[0]["labels"]) == [{"name": "phish", "color": "#ff0000"}]
    assert related_alert.events[0]["vega_label_names"] == "phish"
    assert json.loads(related_alert.events[1]["labels"]) == [{"name": "phish", "color": "#ff0000"}]
    assert related_alert.events[1]["vega_label_names"] == "phish"
    assert json.loads(standalone.events[0]["labels"]) == [{"name": "noise", "color": "#888888"}]
    assert len(standalone.events) == 1


def test_packager_keeps_empty_labels_and_incident_tag_names() -> None:
    case_title = "Vega Incident - VINC-1 - Campaign"
    incident = set_soar_meta(
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "labels": [],
        },
        grouping_id="Vega:incident:inc-1",
        case_tags=["campaign"],
        case_title=case_title,
        incident_id="inc-1",
        is_incident_case=True,
    )
    related_empty = set_soar_meta(
        {
            "id": "alert-1",
            "vegaAlertId": "VALERT-1",
            "name": "Phish",
            "labels": [],
        },
        grouping_id="Vega:incident:inc-1:related",
        case_title=f"{case_title} (related alerts)",
        incident_id="inc-1",
        incident_label_tags=["campaign"],
        is_incident_case=True,
    )
    overflow = set_soar_meta(
        {
            "id": "alert-4",
            "vegaAlertId": "VALERT-4",
            "name": "Beacon",
            "labels": [{"name": "beacon"}],
        },
        grouping_id="Vega:incident:inc-1:related",
        case_tags=["campaign", "beacon"],
        case_title=f"{case_title} (related alerts)",
        incident_id="inc-1",
        incident_label_tags=["campaign"],
        is_incident_case=True,
        apply_case_tags=True,
        case_part=2,
    )
    unrelated_empty = set_soar_meta(
        {
            "id": "alert-3",
            "vegaAlertId": "VALERT-3",
            "name": "Noise",
        },
        grouping_id="Vega:alert:alert-3",
        case_tags=[],
        is_incident_case=False,
    )
    siemplify = SimpleNamespace(context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default")))
    _install_fake_sdk()
    from core.AlertPackager import create_alerts

    packages = create_alerts(
        [
            (ENTITY_TYPE_INCIDENT, incident),
            (ENTITY_TYPE_ALERT, related_empty),
            (ENTITY_TYPE_ALERT, overflow),
            (ENTITY_TYPE_ALERT, unrelated_empty),
        ],
        siemplify,
    )
    incident_alert, related_alert, overflow_alert, standalone = packages
    assert json.loads(incident_alert.events[0]["labels"]) == []
    assert json.loads(related_alert.events[0]["labels"]) == []
    assert related_alert.events[0]["vega_incident_label_names"] == "campaign"
    assert "vega_label_names" not in related_alert.events[0]
    assert getattr(related_alert, "tags", None) in (None, [], "")
    assert overflow_alert.case_tags is None
    assert overflow_alert.tags is None
    assert json.loads(overflow_alert.events[0]["labels"]) == [{"name": "beacon"}]
    assert overflow_alert.events[0]["vega_incident_label_names"] == "campaign"
    assert json.loads(standalone.events[0]["labels"]) == []
    assert "vega_incident_label_names" not in standalone.events[0]
    assert standalone.case_tags is None


def test_related_alerts_keep_their_own_timestamps() -> None:
    incident = set_soar_meta(
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
            "createdAt": "2026-07-28T11:22:43Z",
            "lastUpdated": "2026-07-29T01:00:00Z",
        },
        grouping_id="Vega:incident:inc-1",
        case_title="Vega Incident - VINC-1 - Campaign",
        is_incident_case=True,
        is_related_batch=False,
    )
    older = set_soar_meta(
        {
            "id": "alert-1",
            "vegaAlertId": "VALERT-1",
            "name": "Phish",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-02T00:00:00Z",
        },
        grouping_id="Vega:incident:inc-1:related",
        case_title="Vega Incident - VINC-1 - Campaign (related alerts)",
        grouping_start="2026-07-28T11:22:43Z",
        grouping_end="2026-07-29T01:00:00Z",
        is_incident_case=True,
        is_related_batch=True,
    )
    newer = set_soar_meta(
        {
            "id": "alert-2",
            "vegaAlertId": "VALERT-2",
            "name": "Beacon",
            "createdAt": "2026-04-05T01:18:35Z",
            "updatedAt": "2026-04-06T02:00:00Z",
            "alert_events": [{"name": "login", "_time": "2026-01-01T00:00:00Z"}],
        },
        grouping_id="Vega:incident:inc-1:related",
        case_title="Vega Incident - VINC-1 - Campaign (related alerts)",
        grouping_start="2026-07-28T11:22:43Z",
        grouping_end="2026-07-29T01:00:00Z",
        is_incident_case=True,
        is_related_batch=True,
    )
    siemplify = SimpleNamespace(context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default")))
    _install_fake_sdk()
    from core.AlertPackager import create_alerts, record_start_end

    packages = create_alerts(
        [
            (ENTITY_TYPE_INCIDENT, incident),
            (ENTITY_TYPE_ALERT, older),
            (ENTITY_TYPE_ALERT, newer),
        ],
        siemplify,
    )
    incident_alert, older_alert, newer_alert = packages
    older_start, older_end = record_start_end(older, 1)
    newer_start, newer_end = record_start_end(newer, 1)
    assert older_alert.start_time == older_start
    assert older_alert.end_time == older_end
    assert newer_alert.start_time == newer_start
    assert newer_alert.end_time == newer_end
    assert incident_alert.start_time != older_alert.start_time
    assert older_alert.start_time != newer_alert.start_time
    assert older_alert.events[0]["created_at"] == "2026-01-01T00:00:00Z"
    assert newer_alert.events[0]["created_at"] == "2026-04-05T01:18:35Z"
    assert newer_alert.events[0]["updated_at"] == "2026-04-06T02:00:00Z"
    assert "vega_alert_created_at" not in newer_alert.events[0]
    assert newer_alert.events[1]["StartTime"] != newer_alert.start_time


def test_record_start_is_created_at_and_end_is_last_update() -> None:
    from core.AlertPackager import record_start_end

    incident_start, incident_end = record_start_end(
        {
            "createdAt": "2026-07-28T11:22:43Z",
            "lastUpdated": "2026-07-29T01:00:00Z",
        },
        1,
    )
    alert_start, alert_end = record_start_end(
        {
            "createdAt": "2026-04-05T01:18:35Z",
            "updatedAt": "2026-04-06T02:00:00Z",
        },
        1,
    )
    assert incident_start == 1_785_237_763_000
    assert incident_end == 1_785_286_800_000
    assert alert_start == 1_775_351_915_000
    assert alert_end == 1_775_440_800_000
    missing_end, missing_end_close = record_start_end({"createdAt": "2024-07-01T00:00:00Z"}, 1)
    assert missing_end == missing_end_close == 1_719_792_000_000


def test_alert_event_uses_time_fields_or_parent_alert() -> None:
    from core.AlertPackager import event_start_end

    parent_start = 1_775_351_915_000
    parent_end = 1_775_440_800_000
    assert event_start_end({"name": "login"}, parent_start, parent_end) == (
        parent_start,
        parent_end,
    )
    assert event_start_end(
        {"time": 0, "_time": "0", "timestamp": "none"},
        parent_start,
        parent_end,
    ) == (parent_start, parent_end)
    assert event_start_end({"_time": 1_720_000_000}, parent_start, parent_end) == (
        1_720_000_000_000,
        1_720_000_000_000,
    )
    start, end = event_start_end(
        {
            "createdAt": "2024-07-01T00:00:00Z",
            "_time": "2026-01-01T00:00:00Z",
            "end_time": "2026-01-02T00:00:00Z",
        },
        parent_start,
        parent_end,
    )
    assert start == 1_767_225_600_000
    assert end == 1_767_312_000_000


def test_overflow_incident_uses_unique_ticket_and_same_case_title() -> None:
    overflow = set_soar_meta(
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "VINC-1",
            "name": "Campaign",
        },
        grouping_id="Vega:incident:inc-1:part:2",
        case_title="Vega Incident - VINC-1 - Campaign (part 2)",
        ticket_suffix="part:2",
        case_part=2,
        is_incident_case=True,
    )
    siemplify = SimpleNamespace(context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default")))
    _install_fake_sdk()
    from core.AlertPackager import create_alerts

    packages = create_alerts([(ENTITY_TYPE_INCIDENT, overflow)], siemplify)
    assert len(packages) == 1
    alert = packages[0]
    assert alert.ticket_id == "Vega:inc-1:part:2"
    assert alert.display_id == "Vega:inc-1:part:2"
    assert alert.name.startswith("Vega Incident - VINC-1 - Campaign")
    assert alert.device_product == "Vega"
    assert alert.source_grouping_identifier == "Vega:incident:inc-1:part:2"
    assert alert.rule_generator == "Vega Incident - VINC-1 - Campaign (part 2)"
