from __future__ import annotations

import pathlib

import pytest

from TIPCommon.types import SingleJson

from google_threat_intelligence.connectors import gti_alerts_connector
from google_threat_intelligence.core.data_models import GTIAlert
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from google_threat_intelligence.tests.common import INTEGRATION_PATH

from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata


DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH / 'connectors' / "gti_alerts_connector.yaml"
)

DEFAULT_PARAMETERS: SingleJson = {
    "API Root": "https://threatintelligence.googleapis.com/v1beta/projects/gti-test",
    "API Key": "83a8296ff79e3a8d58d1fc36e00ebd8f9a63735f27619239d445d196fcfb1570",
    "EventClassId": "eventType",
    "DeviceProductField": "Product Name",
    "Max Alerts To Fetch": 10,
    "Max Hours Backwards": 1,
    "Verify SSL": True,
    "Use dynamic list as a blocklist": True,
    "Alert Type Filter": "",
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_gti_alerts_connector_execution(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
) -> None:
    set_is_test_run_to_true()

    connector = gti_alerts_connector.GTIAlertsConnector(
        "GoogleThreatIntelligence - GTI Alerts Connector"
    )
    connector.start()

    assert len(script_session.request_history) >= 2

    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 1

    alert_info = alerts[0]
    assert alert_info.name == "Google Threat Intelligence Credential Alert"
    assert alert_info.rule_generator == "leaked_credentials"
    assert alert_info.priority == 80
    assert alert_info.extensions == {
        "RiskScore": 80,
        "Severity": "High",
    }

    events = alert_info.events
    assert len(events) >= 3

    event_types = [e.get("eventType") for e in events]
    assert "Alert" in event_types
    assert "Finding" in event_types
    assert "Entity" in event_types

    entity_events = [e for e in events if e.get("eventType") == "Entity"]
    entity_values = [e.get("entity_value") for e in entity_events]
    assert "198.51.100.10" in entity_values
    assert "198.51.100.11" in entity_values
    # auth.cymbalbank.com is a single element in Domains (len == 1),
    # so per PM rule it stays inside Finding event
    finding_event = next(e for e in events if e.get("eventType") == "Finding")
    assert (
        finding_event.get("Domains_1") == "auth.cymbalbank.com"
        or finding_event.get("Domains") == "auth.cymbalbank.com"
    )


COMPREHENSIVE_PARAMETERS: SingleJson = {
    "API Root": "https://threatintelligence.googleapis.com/v1beta/projects/gti-comprehensive-project",
    "API Key": "comprehensive_secret_key_999",
    "EventClassId": "eventType",
    "DeviceProductField": "Product Name",
    "PythonProcessTimeout": 300,
    "Environment Field Name": "env_name",
    "Environment Regex Pattern": "(.*)",
    "Verify SSL": True,
    "Lowest Severity To Fetch": "MEDIUM",
    "Alert Type Filter": "leaked_credentials,data_leak",
    "Disable Overflow": True,
    "Max Hours Backwards": 2,
    "Max Alerts To Fetch": 10,
    "Use dynamic list as a blocklist": True,
    "Proxy Server Address": "http://127.0.0.1:8080",
    "Proxy Username": "proxy_user",
    "Proxy Password": "proxy_password",
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=COMPREHENSIVE_PARAMETERS,
)
def test_gti_alerts_connector_comprehensive_parameters(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
) -> None:
    set_is_test_run_to_true()

    connector = gti_alerts_connector.GTIAlertsConnector(
        "GoogleThreatIntelligence - GTI Alerts Connector"
    )
    connector.start()

    assert connector.params.api_root == (
        "https://threatintelligence.googleapis.com/v1beta/projects/gti-comprehensive-project"
    )
    assert connector.params.api_key == "comprehensive_secret_key_999"
    assert connector.params.event_class_id == "eventType"
    assert connector.params.device_product_field == "Product Name"
    assert connector.params.python_process_timeout == 300
    assert connector.params.environment_field_name == "env_name"
    assert connector.params.environment_regex_pattern == "(.*)"
    assert connector.params.verify_ssl is True
    assert connector.params.lowest_severity_to_fetch == "MEDIUM"
    assert connector.params.alert_type_filter == ["leaked_credentials", "data_leak"]
    assert connector.params.disable_overflow is True
    assert connector.params.max_hours_backwards == 2
    assert connector.params.max_alerts_to_fetch == 10
    assert connector.params.use_dynamic_list_as_a_blocklist is True
    assert connector.params.proxy_server_address == "http://127.0.0.1:8080"
    assert connector.params.proxy_username == "proxy_user"
    assert connector.params.proxy_password == "proxy_password"
    assert len(script_session.request_history) >= 3

    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 1
    alert_info = alerts[0]
    assert alert_info.ticket_id == "projects/gti-comprehensive-project/alerts/mock_gti_comprehensive_301"
    assert alert_info.name == "Comprehensive Google Threat Intelligence Alert"
    assert alert_info.rule_generator == "leaked_credentials"
    assert alert_info.priority == 80
    assert alert_info.environment == "Production-US-East"
    assert alert_info.device_product == "Google Threat Intelligence"


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=COMPREHENSIVE_PARAMETERS,
)
def test_gti_alerts_connector_comprehensive_events(
    connector_output: MockConnectorOutput,
) -> None:
    set_is_test_run_to_true()

    connector = gti_alerts_connector.GTIAlertsConnector(
        "GoogleThreatIntelligence - GTI Alerts Connector"
    )
    connector.start()

    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 1
    events = alerts[0].events
    assert len(events) >= 9

    event_types = [e.get("eventType") for e in events]
    assert "Alert" in event_types
    assert "Finding" in event_types
    assert "Document" in event_types
    assert "Entity" in event_types

    alert_event = next(e for e in events if e.get("eventType") == "Alert")
    assert alert_event["id"] == "projects/gti-comprehensive-project/alerts/mock_gti_comprehensive_301"
    assert alert_event["title"] == "Comprehensive Google Threat Intelligence Alert"
    assert alert_event["alert_type"] == "leaked_credentials"
    assert alert_event["severity"] == "HIGH"
    assert "Critical credentials" in alert_event["ai_summary"]
    assert alerts[0].description == alert_event["ai_summary"]

    finding_events = [e for e in events if e.get("eventType") == "Finding"]
    _assert_comprehensive_findings(finding_events)

    document_event = next(e for e in events if e.get("eventType") == "Document")
    _assert_comprehensive_document(document_event)


def _assert_comprehensive_findings(finding_events: list[SingleJson]) -> None:
    """Verify detailed assertions on finding events."""
    assert len(finding_events) == 2
    finding_names = [e["id"] for e in finding_events]
    assert "projects/gti-comprehensive-project/findings/mock_finding_c301_a" in finding_names
    assert "projects/gti-comprehensive-project/findings/mock_finding_c301_b" in finding_names

    finding_b = next(e for e in finding_events if "mock_finding_c301_b" in e["id"])
    assert finding_b["provider"] == "GTI Certificate Intelligence"
    assert finding_b["hash"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert finding_b["filename"] == "cymbalbank_private_key.pem"
    assert finding_b["url"] == "https://example.com/raw/leaked_key_99"
    assert finding_b["threat_actor"] == "UNC2452"

    finding_a = next(e for e in finding_events if "mock_finding_c301_a" in e["id"])
    assert finding_a["user"] == "db_admin@cymbalbank.com"
    assert finding_a["IPs_1"] == "198.51.100.45"
    assert finding_a["Domains_1"] == "db1.cymbalbank.com"


def _assert_comprehensive_document(document_event: SingleJson) -> None:
    """Verify detailed assertions on document event."""
    assert "mock_doc_301" in document_event["id"]
    expected_alert_id = "projects/gti-comprehensive-project/alerts/mock_gti_comprehensive_301"
    assert document_event["alert_id"] == expected_alert_id
    assert document_event["sourceUri"] == "https://darkweb.example.onion/dump/99"
    assert document_event["url"] == "https://darkweb.example.onion/dump/99"
    assert document_event["author"] == "dark_threat_actor"


@pytest.mark.usefixtures("script_session")
@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_gti_alerts_connector_skips_existing_ids(
    monkeypatch: pytest.MonkeyPatch,
    connector_output: MockConnectorOutput,
) -> None:
    set_is_test_run_to_true()
    monkeypatch.setattr(
        gti_alerts_connector,
        "read_ids",
        lambda *_: ["projects/gti-test/alerts/mock_gti_101"],
    )

    connector = gti_alerts_connector.GTIAlertsConnector(
        "GoogleThreatIntelligence - GTI Alerts Connector"
    )
    logged_messages: list[str] = []
    original_info = connector.siemplify.LOGGER.info
    monkeypatch.setattr(
        connector.siemplify.LOGGER,
        "info",
        lambda msg: (logged_messages.append(msg), original_info(msg)),
    )
    connector.start()

    alerts = connector_output.results.json_output.alerts
    assert len(alerts) == 0
    assert any(
        "The alert projects/gti-test/alerts/mock_gti_101 skipped since it has been fetched before"
        in msg
        for msg in logged_messages
    )


@pytest.mark.usefixtures("script_session")
@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_gti_alerts_connector_priority_and_risk_score_mapping() -> None:
    set_is_test_run_to_true()

    raw_alert = {
        "name": "projects/gti-test/alerts/a48175f4-87c2-41bc-a920-d4c5bd941eaa",
        "displayName": "Compromised Citrix Access Directly Targeting Cymbal Bank",
        "detail": {
            "detailType": "initial_access_broker",
            "initialAccessBroker": {"severity": "HIGH"},
        },
        "severityAnalysis": {"severityLevel": "SEVERITY_LEVEL_HIGH"},
        "priorityAnalysis": {"priorityLevel": "PRIORITY_LEVEL_CRITICAL"},
        "aiSummary": "A threat actor is selling Citrix gateway access.",
        "audit": {
            "createTime": "2026-03-12T19:27:35.650624580Z",
            "updateTime": "2026-03-12T19:27:35.650624580Z",
        },
    }
    alert = GTIAlert.from_json(raw_alert)
    assert alert.severity == "HIGH"
    assert alert.priority == "CRITICAL"

    connector = gti_alerts_connector.GTIAlertsConnector(
        "GoogleThreatIntelligence - GTI Alerts Connector"
    )
    connector.extract_params()
    alert_info = connector.create_alert_info(alert)

    assert alert_info.priority == 100
    assert alert_info.extensions["RiskScore"] == 100
    assert alert_info.extensions["Severity"] == "High"
