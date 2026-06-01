"""Unit tests for SOCRadar Alarms Connector."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock


def _make_alarm(alarm_id: int = 12345, risk: str = "HIGH", status: str = "OPEN",
                date: str = "2026-05-26 12:00:00") -> dict[str, Any]:
    """Create a mock SOCRadar alarm dict."""
    return {
        "alarm_id": alarm_id,
        "alarm_risk_level": risk,
        "alarm_asset": "test.example.com",
        "alarm_text": "Test alarm text with IP 1.2.3.4",
        "alarm_response": "Investigate immediately",
        "status": status,
        "date": date,
        "notification_id": 1001,
        "alarm_type_details": {
            "alarm_generic_title": "Test Alarm",
            "alarm_main_type": "Deep & Dark Web Monitoring",
            "alarm_sub_type": "Dark Web Suspicious Content",
            "alarm_default_mitigation_plan": "Block the IP",
            "alarm_detection_and_analysis": "Detected via threat feed",
            "alarm_compliance_list": [],
        },
        "content": {
            "compromised_ips": "1.2.3.4",
            "compromised_emails": "user@test.com",
        },
        "tags": ["malware"],
        "alarm_assignees": [],
        "alarm_related_assets": [],
        "alarm_related_entities": [],
        "is_approved": False,
    }


# -- Helper functions --


def test_parse_date() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import _parse_date
    # Valid date
    ts = _parse_date("2026-05-26 12:00:00")
    expected = int(datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert ts == expected


def test_parse_date_none() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import _parse_date
    ts = _parse_date(None)
    assert ts > 0  # Returns unix_now()


def test_parse_date_invalid() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import _parse_date
    ts = _parse_date("not-a-date")
    assert ts > 0  # Returns unix_now()


def test_parse_date_safe() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import _parse_date_safe
    assert _parse_date_safe(None) == 0
    assert _parse_date_safe("invalid") == 0
    assert _parse_date_safe("2026-05-26 12:00:00") > 0


def test_is_public_ip() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import _is_public_ip
    assert _is_public_ip("8.8.8.8") is True
    assert _is_public_ip("192.168.1.1") is False
    assert _is_public_ip("10.0.0.1") is False
    assert _is_public_ip("127.0.0.1") is False
    assert _is_public_ip("not-an-ip") is False


def test_split_csv() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import _split_csv
    assert _split_csv(None) == []
    assert _split_csv("a,b,c") == ["a", "b", "c"]
    assert _split_csv(["x", "y"]) == ["x", "y"]
    assert _split_csv("") == []


def test_safe_str() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import _safe_str
    assert _safe_str(None) == ""
    assert _safe_str("hello") == "hello"
    assert _safe_str(["first", "second"]) == "first"
    assert _safe_str([]) == ""


# -- Indicator extraction --


def test_extract_indicators() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import _extract_indicators
    alarm = _make_alarm()
    indicators = _extract_indicators(alarm)
    assert "1.2.3.4" in indicators["ips"]
    assert "user@test.com" in indicators["emails"]


def test_extract_indicators_empty() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import _extract_indicators
    alarm = {"content": {}, "alarm_text": ""}
    indicators = _extract_indicators(alarm)
    assert indicators["ips"] == []
    assert indicators["domains"] == []


# -- Alert building --


def test_build_alert() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import build_alert
    siemplify = MagicMock()
    siemplify.extract_connector_param = MagicMock(return_value="")
    siemplify.context.connector_info.environment = "Default Environment"
    alarm = _make_alarm()

    alert = build_alert(siemplify, alarm, company_id="330", extract_indicators=True)

    assert alert.display_id == "12345"
    assert "[#12345]" in alert.name
    assert alert.device_vendor == "SOCRadar"
    assert alert.device_product == "SOCRadar CTI"
    assert alert.priority == 70  # HIGH
    assert len(alert.events) >= 1  # At least base event


def test_build_alert_no_indicators() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import build_alert
    siemplify = MagicMock()
    siemplify.extract_connector_param = MagicMock(return_value="")
    siemplify.context.connector_info.environment = "Default Environment"
    alarm = _make_alarm()

    alert = build_alert(siemplify, alarm, company_id="330", extract_indicators=False)

    assert len(alert.events) == 1  # Only base event


def test_build_alert_missing_atd() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import build_alert
    siemplify = MagicMock()
    siemplify.extract_connector_param = MagicMock(return_value="")
    siemplify.context.connector_info.environment = "Default Environment"
    alarm = _make_alarm()
    alarm["alarm_type_details"] = None  # Missing

    alert = build_alert(siemplify, alarm, company_id="330")
    assert alert.display_id == "12345"  # Should not crash


# -- Risk score mapping --


def test_risk_score_mapping() -> None:
    from socradar_xti.connectors.SOCRadarAlarmsConnector import RISK_SCORE_MAP
    assert RISK_SCORE_MAP["CRITICAL"] == 90
    assert RISK_SCORE_MAP["HIGH"] == 70
    assert RISK_SCORE_MAP["MEDIUM"] == 50
    assert RISK_SCORE_MAP["LOW"] == 30
    assert RISK_SCORE_MAP["INFO"] == 10
