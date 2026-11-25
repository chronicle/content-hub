import json
from types import SimpleNamespace

from core.case_insight import (
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


def test_build_incident_insight_includes_overflow_summary() -> None:
    payload = json.loads(
        build_incident_insight(
            {
                "id": "inc-1",
                "name": "Campaign",
                "severity": "HIGH",
                "incidentSummary": "summary goes to case description",
                "alertsCount": 312,
                "link": "https://vega.io/incidents/inc-1",
            },
            signals_in_case=30,
        )
    )
    assert payload["signals_summary"] == "312 signals, 30 in case"
    assert payload["signals_in_case"] == 30
    assert payload["name"] == "Campaign"
    assert payload["vega_incident_link"] == "https://vega.io/incidents/inc-1"
    assert "incidentSummary" not in payload


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
