import json
from types import SimpleNamespace

from core.case_insight import (
    build_case_description,
    build_incident_insight,
    extract_incident_id_from_ticket,
    incident_ids_from_soar_alert,
)


def test_extract_incident_id_from_ticket() -> None:
    assert (
        extract_incident_id_from_ticket("Vega:incident:abc-123:signal:alert-9")
        == "abc-123"
    )
    assert extract_incident_id_from_ticket("Vega:incident:abc-123") == "abc-123"
    assert extract_incident_id_from_ticket("other") == ""


def test_build_case_description_verdict_then_summary() -> None:
    text = build_case_description(
        {
            "verdict": "MALICIOUS",
            "verdictReasoning": "AI found phishing",
            "incidentSummary": "Campaign summary",
        }
    )
    assert text.startswith("MALICIOUS — AI found phishing")
    assert "Campaign summary" in text


def test_build_incident_insight_key_value_labels() -> None:
    insight = build_incident_insight(
        {
            "id": "inc-1",
            "vegaUniqueIncidentId": "INC-1",
            "name": "Campaign",
            "severity": "HIGH",
            "verdict": "MALICIOUS",
            "investigationStatus": "NEW",
            "incidentSummary": "summary goes to case description",
            "incidentFindings": "findings text",
            "recommendedActions": [{"name": "block"}],
            "typedAssets": [{"value": "host-1", "type": "hostname"}],
            "typedObservables": [{"value": "1.1.1.1", "type": "ip"}],
            "alertsCount": 312,
            "alerts": [{"alertId": "a1", "name": "Phish", "createdAt": "2026-01-01T00:00:00Z"}],
            "link": "https://vega.io/incidents/inc-1",
        },
        signals_in_case=30,
    )
    assert "<strong>Vega Incident ID: </strong>INC-1" in insight
    assert "<strong>Vega Verdict: </strong>MALICIOUS" in insight
    assert "<strong>Vega Incident Severity: </strong>HIGH" in insight
    assert "<strong>Vega Signals: </strong>312 total, 30 in case" in insight
    assert "<strong>Incident Findings: </strong>findings text" in insight
    assert "<strong>Assets: </strong>" in insight
    assert "host-1" in insight
    assert "<strong>Observables: </strong>" in insight
    assert "1.1.1.1" in insight
    assert "https://vega.io/incidents/inc-1" in insight
    assert not insight.strip().startswith("{")


def test_incident_ids_from_soar_alert_parses_json_props() -> None:
    alert = SimpleNamespace(
        ticket_id=None,
        display_id=None,
        identifier=None,
        device_vendor="Vega",
        device_product="Vega",
        additional_properties=json.dumps(
            {
                "vega_incident_id": "inc-42",
                "SourceGroupingIdentifier": "Vega:incident:inc-42",
            }
        ),
    )
    assert incident_ids_from_soar_alert(alert) == ["inc-42"]


def test_incident_ids_from_soar_alert_reads_alert_group_identifier() -> None:
    # SecOps AlertCard exposes connector source_grouping_identifier here.
    alert = SimpleNamespace(
        ticket_id=None,
        display_id=None,
        identifier="soar-guid-not-vega",
        alert_group_identifier="Vega:incident:inc-99",
        source_grouping_identifier=None,
        device_vendor="Vega",
        device_product="Vega",
        additional_properties=None,
    )
    assert incident_ids_from_soar_alert(alert) == ["inc-99"]
