"""Tests for AlertInfo packaging fields used by SOAR search and grouping."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from core.constants import ENTITY_TYPE_ALERT, ENTITY_TYPE_INCIDENT
from core.mapping import incident_case_title, rank_signals, set_soar_meta, signal_rule_generator, signal_ticket_id


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


def test_signal_ticket_and_rule_generator() -> None:
    assert signal_ticket_id("inc-1", "alert-1") == "Vega:incident:inc-1:signal:alert-1"
    assert signal_rule_generator(1, "Phish") == "ALRT-1 - Phish"
    assert incident_case_title({"vegaUniqueIncidentId": "VINC-1", "name": "Campaign"}) == "VINC-1 - Campaign"


def test_rank_signals_escalated_then_severity_then_oldest() -> None:
    signals = [
        {
            "id": "a",
            "severity": "LOW",
            "createdAt": "2026-01-01T00:00:00Z",
            "escalation": {"status": "NOT_ESCALATED"},
        },
        {
            "id": "b",
            "severity": "CRITICAL",
            "createdAt": "2026-06-01T00:00:00Z",
            "escalation": {"status": "NOT_ESCALATED"},
        },
        {
            "id": "c",
            "severity": "LOW",
            "createdAt": "2026-03-01T00:00:00Z",
            "escalation": {"status": "ESCALATED"},
        },
        {
            "id": "d",
            "severity": "CRITICAL",
            "createdAt": "2026-02-01T00:00:00Z",
            "escalation": {"status": "NOT_ESCALATED"},
        },
    ]
    ranked = rank_signals(signals, 3)
    assert [item["id"] for item in ranked] == ["c", "d", "b"]


def test_rank_signals_hard_drops_non_matching_alert_filters() -> None:
    signals = [
        {
            "id": "keep-high",
            "severity": "HIGH",
            "status": "OPEN",
            "verdict": "MALICIOUS",
            "createdAt": "2026-03-01T00:00:00Z",
            "escalation": {"status": "NOT_ESCALATED"},
        },
        {
            "id": "drop-low",
            "severity": "LOW",
            "status": "OPEN",
            "verdict": "MALICIOUS",
            "createdAt": "2026-01-01T00:00:00Z",
            "escalation": {"status": "ESCALATED"},
        },
        {
            "id": "drop-resolved",
            "severity": "CRITICAL",
            "status": "RESOLVED",
            "verdict": "MALICIOUS",
            "createdAt": "2026-02-01T00:00:00Z",
            "escalation": {"status": "ESCALATED"},
        },
        {
            "id": "keep-critical",
            "severity": "CRITICAL",
            "status": "IN PROGRESS",
            "verdict": "SUSPICIOUS",
            "createdAt": "2026-04-01T00:00:00Z",
            "escalation": {"status": "ESCALATED"},
        },
    ]
    ranked = rank_signals(
        signals,
        10,
        filters={
            "severities": ["HIGH", "CRITICAL"],
            "statuses": ["OPEN", "IN_PROGRESS"],
            "verdicts": None,
        },
    )
    assert [item["id"] for item in ranked] == ["keep-critical", "keep-high"]


def test_packager_only_attaches_vega_alert_events() -> None:
    related = set_soar_meta(
        {
            "id": "alert-1",
            "vegaAlertId": "VALERT-1",
            "name": "Phish",
            "createdAt": "2026-04-05T01:18:35Z",
            "href": "https://vega.io/alerts/alert-1",
            "verdict": "MALICIOUS",
            "mitre": {"mitreTactics": ["TA0001"]},
            "relatedIncidents": [
                {"incidentId": "inc-1", "name": "Current"},
                {"incidentId": "inc-2", "name": "Other"},
            ],
            "alert_events": [{"name": "login"}, {"name": "click"}, {"name": "extra"}],
        },
        case_title="VINC-1 - Campaign",
        incident_id="inc-1",
        incident_display_id="VINC-1",
        incident_name="Campaign",
        signal_rank=1,
    )
    siemplify = SimpleNamespace(context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default")))
    _install_fake_sdk()
    from core.AlertPackager import create_alerts

    packages = create_alerts(
        [(ENTITY_TYPE_ALERT, related)],
        siemplify,
        max_events_in_alert=2,
    )
    assert len(packages) == 1
    signal = packages[0]
    assert signal.rule_generator == "VINC-1 - Campaign"
    assert signal.name == "ALRT-1 - Phish"
    assert signal.ticket_id == "Vega:incident:inc-1:signal:alert-1"
    assert signal.source_grouping_identifier == "Vega:incident:inc-1"
    assert signal.case_tags and signal.case_tags[0] == "Vega"
    assert signal.extensions.get("vega_incident_id") == "inc-1"
    assert signal.extensions.get("vega_signal_id") == "VALERT-1"
    assert signal.extensions.get("vega_signal_link") == "https://vega.io/alerts/alert-1"
    assert signal.extensions.get("source_system_url") == "https://vega.io/alerts/alert-1"
    assert signal.extensions.get("signal_verdict") == "MALICIOUS"
    assert signal.extensions.get("also_in") == "inc-2"
    assert signal.extensions.get("alert_type") == "Vega Alert"
    # Only Vega alert-events — no parent event for the Vega alert itself.
    assert len(signal.events) == 2
    assert signal.events[0]["name"] == "login"
    assert signal.events[1]["name"] == "click"


def test_packager_max_events_zero_means_no_secops_events() -> None:
    related = set_soar_meta(
        {
            "id": "alert-1",
            "name": "Phish",
            "alert_events": [{"name": "login"}],
        },
        incident_id="inc-1",
        case_title="VINC-1 - Campaign",
        signal_rank=1,
    )
    siemplify = SimpleNamespace(context=SimpleNamespace(connector_info=SimpleNamespace(environment="Default")))
    _install_fake_sdk()
    from core.AlertPackager import create_alerts

    packages = create_alerts([(ENTITY_TYPE_ALERT, related)], siemplify, max_events_in_alert=0)
    assert packages[0].events == []
