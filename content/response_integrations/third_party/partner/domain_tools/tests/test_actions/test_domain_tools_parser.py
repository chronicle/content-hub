"""Unit tests for DomainToolsParser against real mock_responses.json fixtures."""
from __future__ import annotations

from domain_tools.core.constants import RISK_CATEGORY_HIGH, RISK_CATEGORY_LOW, RISK_CATEGORY_YOUNG
from domain_tools.core.DomainToolsParser import DomainToolsParser
from domain_tools.tests.common import MOCK_RESPONSES

parser = DomainToolsParser()


class TestParseIrisEnrichData:

    def test_high_risk_domain_parsed_correctly(self) -> None:
        raw = MOCK_RESPONSES["iris_enrich_single"]["results"][0]
        result = parser.parse_iris_enrich_data("evil.com", raw)

        assert result.domain == "evil.com"
        assert result.overall_risk_score == 87
        assert result.risk_category == RISK_CATEGORY_HIGH
        assert result.proximity_risk_score == 45
        assert result.malware_risk_score == 72
        assert result.threat_profile_threats == ["malware", "phishing"]
        assert result.threat_profile_evidence == ["blacklisted"]
        assert result.registrant_org == "Unknown LLC"
        assert result.ip_country_code == "ru"
        assert result.create_date == "2024-01-15"

    def test_young_domain_classified_as_young(self) -> None:
        raw = MOCK_RESPONSES["iris_enrich_young"]["results"][0]
        result = parser.parse_iris_enrich_data("newdomain.com", raw)

        assert result.domain == "newdomain.com"
        assert result.risk_category == RISK_CATEGORY_YOUNG
        assert result.is_young_domain is True

    def test_low_risk_domain_parsed_correctly(self) -> None:
        raw = MOCK_RESPONSES["iris_enrich_low_risk"]["results"][0]
        result = parser.parse_iris_enrich_data("google.com", raw)

        assert result.domain == "google.com"
        assert result.overall_risk_score == 5
        assert result.risk_category == RISK_CATEGORY_LOW
        assert result.registrant_org == "Google LLC"
        assert result.ip_country_code == "us"

    def test_missing_create_date_does_not_raise(self) -> None:
        raw = {"domain": "nodatetest.com", "domain_risk": {"risk_score": 10, "components": []}}
        result = parser.parse_iris_enrich_data("nodatetest.com", raw)

        assert result.create_date is None
        assert result.domain_age_days is None

    def test_iris_investigate_link_format(self) -> None:
        raw = MOCK_RESPONSES["iris_enrich_single"]["results"][0]
        result = parser.parse_iris_enrich_data("evil.com", raw)

        assert result.iris_investigate_link == (
            'https://iris.domaintools.com/investigate/search/?q=domain:"evil.com"'
        )
