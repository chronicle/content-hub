"""Tests for SpyCloud severity 30 (stolen session identity / session cookie theft)."""

from __future__ import annotations

from spy_cloud_enterprise.core import Parser
from spy_cloud_enterprise.core.spycloud_udm_converter import SpyCloudUdmConverter


class TestConverterSeverity30:
    """Severity 30 classification in the UDM converter."""

    def test_maps_to_critical(self) -> None:
        converter = SpyCloudUdmConverter()
        assert converter.map_spycloud_to_severity_label(30) == "critical"

    def test_risk_score_is_max(self) -> None:
        converter = SpyCloudUdmConverter()
        assert converter.calculate_risk_score({"severity": 30}) == 100

    def test_product_event_type_is_session_cookie_theft(self) -> None:
        converter = SpyCloudUdmConverter()
        assert (
            converter.get_product_event_type({"severity": 30})
            == "SpyCloud Session Cookie Theft"
        )

    def test_security_summary_describes_stolen_session(self) -> None:
        converter = SpyCloudUdmConverter()
        summary = converter.build_security_summary(
            {"severity": 30, "email": "victim@example.com"}
        )
        assert "stolen session" in summary
        assert "victim@example.com" in summary

    def test_sev30_with_malware_fields_is_not_classified_as_malware(self) -> None:
        """A sev30 record carrying malware-ish fields must keep its own classification."""
        converter = SpyCloudUdmConverter()
        record = {"severity": 30, "email": "victim@example.com", "log_id": "abc123"}
        assert converter.get_product_event_type(record) == "SpyCloud Session Cookie Theft"
        assert "stolen session" in converter.build_security_summary(record)


class TestParserSeverity30:
    """Severity 30 naming in the UDM parser builders."""

    @staticmethod
    def _udm_event() -> dict:
        return {
            "extensions": {"severity": 30, "email": "victim@example.com"},
            "metadata": {},
        }

    def test_rule_generator(self) -> None:
        assert (
            Parser.build_rule_generator_from_udm(self._udm_event())
            == "SpyCloud Session Cookie Theft"
        )

    def test_event_name(self) -> None:
        assert (
            Parser.build_event_name_from_udm(self._udm_event())
            == "SpyCloud Session Cookie Theft"
        )

    def test_alert_name_includes_identifier(self) -> None:
        assert (
            Parser.build_alert_name_from_udm(self._udm_event())
            == "SpyCloud Session Cookie Theft - victim@example.com"
        )
