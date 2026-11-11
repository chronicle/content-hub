from __future__ import annotations

import copy
import pathlib

import pytest
from TIPCommon.types import SingleJson

from google_threat_intelligence.connectors import dtm_alerts_connector
from google_threat_intelligence.tests.common import INTEGRATION_PATH
from google_threat_intelligence.tests.core.session import (
    GoogleThreatIntelligenceSession,
)
from google_threat_intelligence.tests.responses.api import common_responses

from integration_testing.common import set_is_test_run_to_true, set_is_test_run_to_false
from integration_testing.platform.script_output import MockConnectorOutput
from integration_testing.set_meta import set_metadata


DEF_PATH: pathlib.Path = (
    INTEGRATION_PATH / 'connectors' / "dtm_alerts_connector.yaml"
)

DEFAULT_PARAMETERS: SingleJson = {
    "API Root": "https://www.virustotal.com",
    "API Key": "the key",
    "EventClassId": "event_type",
    "DeviceProductField": "Product Name",
    "Max Alerts To Fetch": 25,
    "Max Hours Backwards": 1,
    "Verify SSL": True,
    "Use dynamic list as a blocklist": True,
    "Monitor Name Filter": "",
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_dtm_alerts_connector(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
):
    set_is_test_run_to_true()

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path == "/api/v3/dtm/alerts"

    assert len(connector_output.results.json_output.alerts) == 1


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=DEFAULT_PARAMETERS,
)
def test_dtm_alerts_connector_has_main_alert_event(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
):
    set_is_test_run_to_true()

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path == "/api/v3/dtm/alerts"

    assert len(connector_output.results.json_output.alerts) == 1

    events = connector_output.results.json_output.alerts[0].events
    assert len(events) == 5
    assert events[0]["event_type"] == "Main Alert"


INCLUSION_FILTER_PARAMETERS: SingleJson = {
    **DEFAULT_PARAMETERS,
    "Event Type Filter": "domain",
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=INCLUSION_FILTER_PARAMETERS,
)
def test_dtm_alerts_connector_inclusion_filter_for_event_type(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
):
    set_is_test_run_to_true()

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path == "/api/v3/dtm/alerts"

    assert len(connector_output.results.json_output.alerts) == 1

    events = connector_output.results.json_output.alerts[0].events
    assert len(events) == 4

    main_event = events[0]
    assert main_event["event_type"] == "Main Alert"

    filtered_events = events[1:]
    assert all(event["event_type"] == "domain" for event in filtered_events)


EXCLUSION_FILTER_PARAMETERS: SingleJson = {
    **DEFAULT_PARAMETERS,
    "Event Type Filter": "!domain",
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=EXCLUSION_FILTER_PARAMETERS,
)
def test_dtm_alerts_connector_exclusion_filter_for_event_type(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
):
    set_is_test_run_to_true()

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path == "/api/v3/dtm/alerts"

    assert len(connector_output.results.json_output.alerts) == 1

    events = connector_output.results.json_output.alerts[0].events
    assert len(events) == 2

    main_event = events[0]
    assert main_event["event_type"] == "Main Alert"

    filtered_events = events[1:]
    assert all(event["event_type"] != "domain" for event in filtered_events)


EXCLUDE_ALL_EXCLUSION_FILTER_PARAMETERS: SingleJson = {
    **DEFAULT_PARAMETERS,
    "Event Type Filter": "!domain,!ipv4_address",
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=EXCLUDE_ALL_EXCLUSION_FILTER_PARAMETERS,
)
def test_dtm_alerts_connector_exclude_all_exclusion_filter_for_event_type(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
):
    set_is_test_run_to_true()

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path == "/api/v3/dtm/alerts"

    assert len(connector_output.results.json_output.alerts) == 1

    events = connector_output.results.json_output.alerts[0].events
    assert len(events) == 1

    main_event = events[0]
    assert main_event["event_type"] == "Main Alert"


INCLUDE_NONEXISTENT_INCLUSION_FILTER_PARAMETERS: SingleJson = {
    **DEFAULT_PARAMETERS,
    "Event Type Filter": "nonexistent_filter",
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=INCLUDE_NONEXISTENT_INCLUSION_FILTER_PARAMETERS,
)
def test_dtm_alerts_connector_include_nonexistent_inclusion_filter_for_event_type(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
):
    set_is_test_run_to_true()

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path == "/api/v3/dtm/alerts"

    assert len(connector_output.results.json_output.alerts) == 1

    events = connector_output.results.json_output.alerts[0].events
    assert len(events) == 1

    main_event = events[0]
    assert main_event["event_type"] == "Main Alert"


INCLUSION_AND_EXCLUSION_OVERLAP_FILTER_PARAMETERS: SingleJson = {
    **DEFAULT_PARAMETERS,
    "Event Type Filter": "ipv4_address,!ipv4_address",
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=INCLUSION_AND_EXCLUSION_OVERLAP_FILTER_PARAMETERS,
)
def test_dtm_alerts_connector_allow_filter_priority(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
):
    set_is_test_run_to_true()

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(script_session.request_history) == 1
    assert script_session.request_history[0].request.url.path == "/api/v3/dtm/alerts"

    assert len(connector_output.results.json_output.alerts) == 1

    events = connector_output.results.json_output.alerts[0].events
    assert len(events) == 2

    main_event = events[0]
    assert main_event["event_type"] == "Main Alert"

    filtered_events = events[1:]
    assert all(event["event_type"] == "ipv4_address" for event in filtered_events)


MONITOR_NAME_FILTER_PARAMETERS: SingleJson = {
    **DEFAULT_PARAMETERS,
    "Monitor Name Filter": "monitor_name_1",
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=MONITOR_NAME_FILTER_PARAMETERS,
)
def test_dtm_alerts_connector_monitor_name_filter(
    script_session: GoogleThreatIntelligenceSession,
):
    set_is_test_run_to_true()

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    # 1. List monitors
    # 2. Fetch alerts
    assert len(script_session.request_history) == 2
    assert script_session.request_history[0].request.url.path == "/api/v3/dtm/monitors"
    assert script_session.request_history[1].request.url.path == "/api/v3/dtm/alerts"

    assert "redacted-alert-id" in script_session.request_history[1].request.kwargs.get(
        "params"
    ).get("monitor_id")


ANONYMIZE_PASSWORD_PARAMETERS: SingleJson = {
    **DEFAULT_PARAMETERS,
    "Anonymize Passwords": True,
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=ANONYMIZE_PASSWORD_PARAMETERS,
)
def test_dtm_alerts_connector_anonymize_passwords(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
) -> None:
    """Verify service_account plain_text password is anonymized when enabled."""
    set_is_test_run_to_true()

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(connector_output.results.json_output.alerts) == 1
    events = connector_output.results.json_output.alerts[0].events

    main_event = next(e for e in events if e["event_type"] == "Main Alert")
    assert (
        main_event.get("doc_service_account_password_plain_text")
        == "s********************3"
    )
    assert main_event.get("doc_service_account_login") == "user@example.com"


NO_ANONYMIZE_PASSWORD_PARAMETERS: SingleJson = {
    **DEFAULT_PARAMETERS,
    "Anonymize Passwords": False,
}


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=NO_ANONYMIZE_PASSWORD_PARAMETERS,
)
def test_dtm_alerts_connector_no_anonymize_passwords(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
) -> None:
    """Verify service_account plain_text password remains cleartext when disabled."""
    set_is_test_run_to_true()

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(connector_output.results.json_output.alerts) == 1
    events = connector_output.results.json_output.alerts[0].events

    main_event = next(e for e in events if e["event_type"] == "Main Alert")
    assert (
        main_event.get("doc_service_account_password_plain_text")
        == "supersecretpassword123"
    )
    assert main_event.get("doc_service_account_login") == "user@example.com"


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=ANONYMIZE_PASSWORD_PARAMETERS,
)
def test_dtm_alerts_connector_anonymize_short_password(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify passwords with length <= 2 are fully masked with asterisks."""
    set_is_test_run_to_true()

    modified_response = copy.deepcopy(common_responses.DTM_ALERTS_RESPONSE)
    modified_response["alerts"][0]["doc"]["service_account"]["password"][
        "plain_text"
    ] = "ab"
    monkeypatch.setattr(common_responses, "DTM_ALERTS_RESPONSE", modified_response)

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(connector_output.results.json_output.alerts) == 1
    events = connector_output.results.json_output.alerts[0].events

    main_event = next(e for e in events if e["event_type"] == "Main Alert")
    assert main_event.get("doc_service_account_password_plain_text") == "**"


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=ANONYMIZE_PASSWORD_PARAMETERS,
)
def test_dtm_alerts_connector_does_not_anonymize_passwords_outside_compromised_credential_schema(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify password keys outside doc.service_account are not anonymized."""
    set_is_test_run_to_true()

    modified_response = copy.deepcopy(common_responses.DTM_ALERTS_RESPONSE)
    modified_response["alerts"][0]["doc"]["password"] = "supersecretpassword123"
    monkeypatch.setattr(common_responses, "DTM_ALERTS_RESPONSE", modified_response)

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(connector_output.results.json_output.alerts) == 1
    events = connector_output.results.json_output.alerts[0].events

    main_event = next(e for e in events if e["event_type"] == "Main Alert")
    assert main_event.get("doc_password") == "supersecretpassword123"


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=ANONYMIZE_PASSWORD_PARAMETERS,
)
def test_dtm_alerts_connector_does_not_anonymize_values_containing_password_keyword(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify non-password fields containing the word password are not anonymized."""
    set_is_test_run_to_true()

    modified_response = copy.deepcopy(common_responses.DTM_ALERTS_RESPONSE)
    modified_response["alerts"][0]["doc"]["description"] = (
        "User password has been leaked"
    )
    monkeypatch.setattr(common_responses, "DTM_ALERTS_RESPONSE", modified_response)

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(connector_output.results.json_output.alerts) == 1
    events = connector_output.results.json_output.alerts[0].events

    main_event = next(e for e in events if e["event_type"] == "Main Alert")
    assert main_event.get("doc_description") == "User password has been leaked"


@set_metadata(
    connector_def_file_path=DEF_PATH,
    parameters=ANONYMIZE_PASSWORD_PARAMETERS,
)
def test_dtm_alerts_connector_does_not_anonymize_plain_text_outside_scope(
    script_session: GoogleThreatIntelligenceSession,
    connector_output: MockConnectorOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify plain_text keys outside doc.service_account.password are untouched."""
    set_is_test_run_to_true()

    modified_response = copy.deepcopy(common_responses.DTM_ALERTS_RESPONSE)
    alert = modified_response["alerts"][0]
    alert["doc"]["article"] = {
        "plain_text": "This is a public discussion forum message"
    }
    alert["doc"]["plain_text"] = "Root level plain_text password note"
    alert["doc"]["unrelated_entity"] = {
        "password": {"plain_text": "supersecretpassword123"}
    }
    monkeypatch.setattr(common_responses, "DTM_ALERTS_RESPONSE", modified_response)

    connector = dtm_alerts_connector.DTMAlertsConnector("DTMAlertsFakeConnector")
    connector.start()

    assert len(connector_output.results.json_output.alerts) == 1
    events = connector_output.results.json_output.alerts[0].events

    main_event = next(e for e in events if e["event_type"] == "Main Alert")

    # Scoped password inside doc -> service_account -> password -> plain_text
    # MUST be anonymized.
    assert (
        main_event.get("doc_service_account_password_plain_text")
        == "s********************3"
    )

    # plain_text fields outside doc -> service_account -> password MUST NOT
    # be anonymized.
    assert (
        main_event.get("doc_article_plain_text")
        == "This is a public discussion forum message"
    )
    assert main_event.get("doc_plain_text") == "Root level plain_text password note"
    assert (
        main_event.get("doc_unrelated_entity_password_plain_text")
        == "supersecretpassword123"
    )
