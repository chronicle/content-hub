from __future__ import annotations

import pytest
from TIPCommon.types import SingleJson

from google_threat_intelligence.core.data_models import ASMEntity, GTIAlert

# pylint: disable=redefined-outer-name


@pytest.fixture
def leaked_credentials_alert_payloads() -> tuple[SingleJson, list[SingleJson], list[SingleJson]]:
    """Fixture returning raw alert, findings, and documents for leaked credentials test."""
    raw_alert: SingleJson = {
        "name": "projects/gti-test/alerts/alert-123",
        "displayName": "Leaked Credentials Alert",
        "detail": {
            "detailType": "leaked_credentials",
            "leakedCredentials": {"severity": "HIGH"},
        },
        "severityAnalysis": {"severityLevel": "SEVERITY_LEVEL_HIGH"},
        "aiSummary": "Leaked credentials detected for Cymbal Bank.",
        "tags": ["critical", "finance"],
        "categories": ["credential_theft", "darkweb"],
        "audit": {"createTime": "2026-09-15T10:00:00Z"},
    }
    finding_details: list[SingleJson] = [
        {
            "name": "projects/gti-test/findings/finding-456",
            "displayName": "Compromised Admin Account",
            "provider": "GTI Threat Engine",
            "aiSummary": "User credentials leaked on dark web forum.",
            "user": "admin@cymbalbank.com",
            "IPs": ["198.51.100.101", "198.51.100.102"],
            "Domains": ["auth.cymbalbank.com"],
            "references": ["https://internal.wiki/doc1", "https://internal.wiki/doc2"],
            "audit": {"createTime": "2026-09-15T10:00:00Z"},
        }
    ]
    documents_details: list[SingleJson] = [
        {
            "name": "projects/gti-test/alerts/alert-123/documents/doc-789",
            "title": "Insider Job Posting",
            "sourceUri": "http://darkweb.onion/leak/1",
            "author": "anonymous_leaker",
            "createTime": "2026-09-15T10:01:00Z",
            "translation": {
                "translatedTitle": "Insider Job Posting (Translated)",
            },
        }
    ]
    return raw_alert, finding_details, documents_details


@pytest.fixture
def data_leak_cve_alert_payloads() -> tuple[SingleJson, list[SingleJson], list[SingleJson]]:
    """Fixture returning raw alert, findings, and documents for data leak CVE test."""
    raw_alert_data_leak: SingleJson = {
        "name": "projects/gti-test/alerts/leak-100",
        "displayName": "Data Leak with CVE Reference",
        "detail": {
            "detailType": "data_leak",
            "dataLeak": {
                "cveId": "CVE-2024-38077",
                "severity": "HIGH",
            },
        },
        "findings": ["projects/gti-test/findings/finding-100"],
    }
    findings_details: list[SingleJson] = [
        {
            "name": "projects/gti-test/findings/finding-100",
            "displayName": "Finding with Exploit Link",
            "provider": "GTI Threat Engine",
            "audit": {"createTime": "2026-09-15T12:00:00Z"},
        }
    ]
    documents_details: list[SingleJson] = [
        {
            "name": "projects/gti-test/alerts/leak-100/documents/doc-100",
            "title": "Dark Web Forum Exploit Post",
            "sourceUri": "https://example.onion/post/100",
            "user_name": "citrix-lord",
            "createTime": "2026-09-15T12:05:00Z",
        }
    ]
    return raw_alert_data_leak, findings_details, documents_details


def test_asm_entity_from_json_escapes_script_tags() -> None:
    raw_data = {
        "name": "test_entity",
        "details": {"extended_response_body": "<html><script>alert(1)</script></html>"},
    }
    entity = ASMEntity.from_json(raw_data)
    assert (
        entity.raw_data["details"]["extended_response_body"]
        == "<html><script>alert(1)<\\/script></html>"
    )


def test_asm_entity_from_json_no_extended_response_body() -> None:
    raw_data = {"name": "test_entity", "details": {"port": 80}}
    entity = ASMEntity.from_json(raw_data)
    assert "extended_response_body" not in entity.raw_data["details"]


def test_gti_alert_from_json_and_to_events(
    leaked_credentials_alert_payloads: tuple[SingleJson, list[SingleJson], list[SingleJson]],
) -> None:
    raw_alert, finding_details, documents_details = leaked_credentials_alert_payloads
    alert = GTIAlert.from_json(
        raw_alert,
        findings_details=finding_details,
        documents_details=documents_details,
    )
    assert alert.alert_id == "projects/gti-test/alerts/alert-123"
    assert alert.display_name == "Leaked Credentials Alert"
    assert alert.severity == "HIGH"

    events = alert.to_events()
    assert len(events) == 5
    event_types = [e.get("eventType") for e in events]
    assert "Alert" in event_types
    assert "Finding" in event_types
    assert "Document" in event_types
    assert "Entity" in event_types

    alert_event = next(e for e in events if e.get("eventType") == "Alert")
    assert alert_event["id"] == "projects/gti-test/alerts/alert-123"
    assert alert_event["title"] == "Leaked Credentials Alert"
    finding_event = next(e for e in events if e.get("eventType") == "Finding")
    assert finding_event["id"] == "projects/gti-test/findings/finding-456"
    assert finding_event["alert_id"] == "projects/gti-test/alerts/alert-123"
    document_event = next(e for e in events if e.get("eventType") == "Document")
    assert document_event["id"] == "projects/gti-test/alerts/alert-123/documents/doc-789"
    assert document_event["alert_id"] == "projects/gti-test/alerts/alert-123"
    assert document_event["sourceUri"] == "http://darkweb.onion/leak/1"
    assert document_event["url"] == "http://darkweb.onion/leak/1"
    assert document_event["author"] == "anonymous_leaker"
    assert document_event["translation_translatedTitle"] == "Insider Job Posting (Translated)"


def test_gti_alert_extract_severity_naming_conventions() -> None:
    # Case 1: snake_case detailType matching camelCase sub-object
    raw_alert_camel = {
        "name": "projects/p/alerts/a1",
        "detail": {
            "detailType": "leaked_credentials",
            "leakedCredentials": {"severity": "CRITICAL"},
        },
        "severityAnalysis": {"severityLevel": "SEVERITY_LEVEL_LOW"},
    }
    alert1 = GTIAlert.from_json(raw_alert_camel)
    assert alert1.severity == "CRITICAL"

    # Case 2: snake_case detailType matching exact snake_case sub-object
    raw_alert_snake = {
        "name": "projects/p/alerts/a2",
        "detail": {
            "detailType": "domain_abuse",
            "domain_abuse": {"severity": "MEDIUM"},
        },
        "severityAnalysis": {"severityLevel": "SEVERITY_LEVEL_LOW"},
    }
    alert2 = GTIAlert.from_json(raw_alert_snake)
    assert alert2.severity == "MEDIUM"

    # Case 3: detail has no severity, fall back to severityAnalysis
    raw_alert_fallback = {
        "name": "projects/p/alerts/a3",
        "detail": {
            "detailType": "unknown_type",
        },
        "severityAnalysis": {"severityLevel": "SEVERITY_LEVEL_HIGH"},
    }
    alert3 = GTIAlert.from_json(raw_alert_fallback)
    assert alert3.severity == "HIGH"

    # Case 4: detail and severityAnalysis both missing, default to MEDIUM
    raw_alert_default = {
        "name": "projects/p/alerts/a4",
    }
    alert4 = GTIAlert.from_json(raw_alert_default)
    assert alert4.severity == "MEDIUM"


def test_gti_alert_extract_severity_vulnerability_match() -> None:
    raw_alert_vuln = {
        "name": "projects/p/alerts/a5",
        "detail": {
            "detailType": "target_technology",
            "targetTechnology": {
                "vulnerabilityMatch": {
                    "cveId": "CVE-2023-3420",
                    "riskRating": "HIGH",
                }
            },
        },
    }
    alert5 = GTIAlert.from_json(raw_alert_vuln)
    assert alert5.severity == "HIGH"
    assert alert5.cve == "CVE-2023-3420"
    events5 = alert5.to_events()
    assert events5[0]["cve"] == "CVE-2023-3420"
    assert events5[0]["cveId"] == "CVE-2023-3420"
    assert events5[0]["cve_id"] == "CVE-2023-3420"
    assert events5[0]["detail_targetTechnology_vulnerabilityMatch_cveId"] == "CVE-2023-3420"


def test_gti_alert_events_ai_summary_falls_back_to_display_name() -> None:
    raw_alert_target_technology = {
        "name": "projects/p/alerts/a6",
        "displayName": "CVE-2020-9547",
        "detail": {
            "detailType": "target_technology",
            "targetTechnology": {"vulnerabilityMatch": {"cveId": "CVE-2020-9547"}},
        },
        "ips": ["198.51.100.1", "198.51.100.2"],
    }
    alert = GTIAlert.from_json(
        raw_alert_target_technology,
        findings_details=[{"name": "projects/p/findings/f6", "provider": "GTI"}],
        documents_details=[{"name": "projects/p/alerts/a6/documents/d6", "title": "Post"}],
    )
    events = alert.to_events()
    assert alert.ai_summary == ""
    assert alert.summary == "CVE-2020-9547"
    assert {e["eventType"] for e in events} == {"Alert", "Finding", "Document", "Entity"}
    assert all(e["ai_summary"] == "CVE-2020-9547" for e in events)


def test_gti_alert_events_ai_summary_prefers_most_specific_value(
    leaked_credentials_alert_payloads: tuple[SingleJson, list[SingleJson], list[SingleJson]],
) -> None:
    raw_alert, finding_details, documents_details = leaked_credentials_alert_payloads
    alert = GTIAlert.from_json(
        raw_alert,
        findings_details=finding_details,
        documents_details=documents_details,
    )
    summaries = {e["eventType"]: e["ai_summary"] for e in alert.to_events()}
    assert summaries["Alert"] == "Leaked credentials detected for Cymbal Bank."
    assert summaries["Finding"] == "User credentials leaked on dark web forum."
    assert summaries["Document"] == "Leaked credentials detected for Cymbal Bank."
    assert summaries["Entity"] == "Leaked credentials detected for Cymbal Bank."


def test_gti_alert_cve_mapping_for_non_target_technology(
    data_leak_cve_alert_payloads: tuple[SingleJson, list[SingleJson], list[SingleJson]],
) -> None:
    raw_alert, findings_details, documents_details = data_leak_cve_alert_payloads
    alert = GTIAlert.from_json(
        raw_alert,
        findings_details=findings_details,
        documents_details=documents_details,
    )

    assert alert.cve == "CVE-2024-38077"
    events = alert.to_events()
    assert len(events) == 3

    alert_event = next(e for e in events if e.get("eventType") == "Alert")
    assert alert_event["alert_type"] == "data_leak"
    assert alert_event["cve"] == alert_event["cve_id"] == alert_event["cveId"] == "CVE-2024-38077"

    finding_event = next(e for e in events if e.get("eventType") == "Finding")
    assert finding_event["alert_type"] == "data_leak"
    assert finding_event["cve"] == finding_event["cve_id"] == finding_event["cveId"] == "CVE-2024-38077"

    document_event = next(e for e in events if e.get("eventType") == "Document")
    assert document_event["alert_type"] == "data_leak"
    assert document_event["cve"] == document_event["cve_id"] == document_event["cveId"] == "CVE-2024-38077"
    assert document_event["user_name"] == "citrix-lord"
    assert document_event["author"] == "citrix-lord"
    assert document_event["userName"] == "citrix-lord"
    assert document_event["user"] == "citrix-lord"
    assert document_event["username"] == "citrix-lord"


def test_gti_alert_cve_mapping_multi_cve_entities() -> None:
    raw_alert_insider = {
        "name": "projects/gti-test/alerts/insider-200",
        "displayName": "Insider Threat with Multi CVEs",
        "detail": {
            "detailType": "insider_threat",
            "insiderThreat": {
                "severity": "CRITICAL",
            },
        },
        "cves": ["CVE-2024-1111", "CVE-2024-2222"],
    }
    alert_multi = GTIAlert.from_json(raw_alert_insider)
    events_multi = alert_multi.to_events()
    assert len(events_multi) == 3
    entity_events = [e for e in events_multi if e.get("eventType") == "Entity"]
    assert len(entity_events) == 2
    cve_values = {e["cve"] for e in entity_events}
    assert cve_values == {"CVE-2024-1111", "CVE-2024-2222"}
    for e in entity_events:
        assert e["alert_type"] == "insider_threat"
        assert e["cve"] == e["cve_id"] == e["cveId"]
