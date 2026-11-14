"""Unit tests for SOCRadar Alarms Connector."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from socradar_xti.connectors import SOCRadarAlarmsConnector as mod
from socradar_xti.connectors.SOCRadarAlarmsConnector import (
    RISK_SCORE_MAP,
    SOAR_PRIORITY_MAP,
    _extract_indicators,
    _is_excluded,
    _is_public_ip,
    _parse_date,
    _parse_date_safe,
    _parse_int_csv,
    _safe_str,
    _split_csv,
    build_alert,
)


def _make_alarm(
    alarm_id: int = 12345, risk: str = "HIGH", status: str = "OPEN", date: str = "2026-05-26 12:00:00"
) -> dict[str, Any]:
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

    # Valid date
    ts = _parse_date("2026-05-26 12:00:00")
    expected = int(datetime(2026, 5, 26, 12, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    assert ts == expected


def test_parse_date_none() -> None:

    ts = _parse_date(None)
    assert ts > 0  # Returns unix_now()


def test_parse_date_invalid() -> None:

    ts = _parse_date("not-a-date")
    assert ts > 0  # Returns unix_now()


def test_parse_date_safe() -> None:

    assert _parse_date_safe(None) == 0
    assert _parse_date_safe("invalid") == 0
    assert _parse_date_safe("2026-05-26 12:00:00") > 0


def test_is_public_ip() -> None:

    assert _is_public_ip("8.8.8.8") is True
    assert _is_public_ip("192.168.1.1") is False
    assert _is_public_ip("10.0.0.1") is False
    assert _is_public_ip("127.0.0.1") is False
    assert _is_public_ip("not-an-ip") is False


def test_split_csv() -> None:

    assert _split_csv(None) == []
    assert _split_csv("a,b,c") == ["a", "b", "c"]
    assert _split_csv(["x", "y"]) == ["x", "y"]
    assert _split_csv("") == []


def test_safe_str() -> None:

    assert _safe_str(None) == ""
    assert _safe_str("hello") == "hello"
    assert _safe_str(["first", "second"]) == "first"
    assert _safe_str([]) == ""


# -- Indicator extraction --


def test_extract_indicators() -> None:

    alarm = _make_alarm()
    indicators = _extract_indicators(alarm)
    assert "1.2.3.4" in indicators["ips"]
    assert "user@test.com" in indicators["emails"]


def test_extract_indicators_empty() -> None:

    alarm = {"content": {}, "alarm_text": ""}
    indicators = _extract_indicators(alarm)
    assert indicators["ips"] == []
    assert indicators["domains"] == []


# -- Alert building --


def test_build_alert() -> None:

    siemplify = MagicMock()
    siemplify.extract_connector_param = MagicMock(return_value="")
    siemplify.context.connector_info.environment = "Default Environment"
    alarm = _make_alarm()

    alert = build_alert(siemplify, alarm, company_id="330", extract_indicators=True)

    assert alert.display_id == "12345"
    assert "[#12345]" in alert.name
    assert alert.device_vendor == "SOCRadar"
    assert alert.device_product == "SOCRadar CTI"
    assert alert.priority == 80  # HIGH -> SOAR High
    assert alert.events[0]["Priority"] == "80"
    assert alert.events[0]["risk_score"] == "70"  # unchanged for existing mappings
    assert len(alert.events) >= 1  # At least base event


def test_build_alert_no_indicators() -> None:

    siemplify = MagicMock()
    siemplify.extract_connector_param = MagicMock(return_value="")
    siemplify.context.connector_info.environment = "Default Environment"
    alarm = _make_alarm()

    alert = build_alert(siemplify, alarm, company_id="330", extract_indicators=False)

    assert len(alert.events) == 1  # Only base event


def test_build_alert_missing_atd() -> None:

    siemplify = MagicMock()
    siemplify.extract_connector_param = MagicMock(return_value="")
    siemplify.context.connector_info.environment = "Default Environment"
    alarm = _make_alarm()
    alarm["alarm_type_details"] = None  # Missing

    alert = build_alert(siemplify, alarm, company_id="330")
    assert alert.display_id == "12345"  # Should not crash


# -- Risk score mapping --


def test_risk_score_mapping() -> None:

    assert RISK_SCORE_MAP["CRITICAL"] == 90
    assert RISK_SCORE_MAP["HIGH"] == 70
    assert RISK_SCORE_MAP["MEDIUM"] == 50
    assert RISK_SCORE_MAP["LOW"] == 30
    assert RISK_SCORE_MAP["INFO"] == 10


def test_soar_priority_mapping() -> None:

    assert SOAR_PRIORITY_MAP == {"CRITICAL": 100, "HIGH": 80, "MEDIUM": 60, "LOW": 40, "INFO": -1}


def test_build_alert_unknown_risk_level_defaults_to_medium() -> None:

    siemplify = MagicMock()
    siemplify.context.connector_info.environment = "Default Environment"
    alarm = _make_alarm()
    alarm["alarm_risk_level"] = "WHATEVER"
    alert = build_alert(siemplify, alarm, company_id="330", extract_indicators=False)
    assert alert.priority == 60


# -- Filter parsing --


def test_parse_int_csv() -> None:

    assert _parse_int_csv("", "X") is None
    assert _parse_int_csv(None, "X") is None
    assert _parse_int_csv(" 12, 45 ,", "X") == [12, 45]
    with pytest.raises(ValueError):
        _parse_int_csv("12, abc", "X")


def test_main_passes_type_filters_to_api(monkeypatch: pytest.MonkeyPatch) -> None:
    params = {
        "API Key": "k",
        "Company ID": "330",
        "Sub Type Filter": "Stolen Credentials",
        "Alarm Type ID Filter": "12, 45",
        "Excluded Main Type Filter": "Attack Surface Management",
        "Excluded Sub Type Filter": "Subdomain Takeover Check, Phishing Domain",
        "Excluded Alarm Type ID Filter": "7",
    }
    siemplify = MagicMock()
    siemplify.extract_connector_param.side_effect = lambda name, default_value=None, input_type=None: params.get(
        name, default_value
    )
    siemplify.fetch_timestamp.return_value = 0
    siemplify.get_connector_context_property.return_value = ""
    manager = MagicMock()
    manager.get_all_incidents.return_value = ([], 0)
    monkeypatch.setattr(mod, "SiemplifyConnectorExecution", lambda: siemplify)
    monkeypatch.setattr(mod, "SOCRadarManager", lambda *a, **k: manager)

    mod.main(is_test_run=True)

    kwargs = manager.get_all_incidents.call_args.kwargs
    assert kwargs["alarm_sub_types"] == ["Stolen Credentials"]
    assert kwargs["alarm_type_ids"] == [12, 45]
    assert kwargs["excluded_alarm_main_types"] == ["Attack Surface Management"]
    assert kwargs["excluded_alarm_sub_types"] == ["Subdomain Takeover Check", "Phishing Domain"]
    assert kwargs["excluded_alarm_type_ids"] == [7]


def test_main_empty_type_filters_send_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    siemplify = MagicMock()
    siemplify.extract_connector_param.side_effect = lambda name, default_value=None, input_type=None: {
        "API Key": "k",
        "Company ID": "330",
    }.get(name, default_value)
    siemplify.fetch_timestamp.return_value = 0
    siemplify.get_connector_context_property.return_value = ""
    manager = MagicMock()
    manager.get_all_incidents.return_value = ([], 0)
    monkeypatch.setattr(mod, "SiemplifyConnectorExecution", lambda: siemplify)
    monkeypatch.setattr(mod, "SOCRadarManager", lambda *a, **k: manager)

    mod.main(is_test_run=True)

    kwargs = manager.get_all_incidents.call_args.kwargs
    for key in ("alarm_type_ids", "excluded_alarm_main_types", "excluded_alarm_sub_types", "excluded_alarm_type_ids"):
        assert kwargs[key] is None


# -- Client-side exclusion guard --


def _typed_alarm(alarm_id: int, main: str, sub: str, type_id: int, date: str) -> dict[str, Any]:
    alarm = _make_alarm(alarm_id=alarm_id, date=date)
    alarm["alarm_type_id"] = type_id
    alarm["alarm_type_details"]["alarm_main_type"] = main
    alarm["alarm_type_details"]["alarm_sub_type"] = sub
    return alarm


def test_is_excluded_matches_names_case_insensitively_including_ampersand() -> None:
    alarm = _typed_alarm(1, "Deep&Dark Web Monitoring", "Stolen Credentials", 1272, "2026-05-26 12:00:00")
    assert _is_excluded(alarm, {"deep&dark web monitoring"}, set(), set()) is True
    assert _is_excluded(alarm, set(), {"stolen credentials"}, set()) is True
    assert _is_excluded(alarm, set(), set(), {"1272"}) is True


def test_is_excluded_false_when_no_filter_matches_or_filters_empty() -> None:
    alarm = _typed_alarm(1, "Brand Protection", "Impersonating Domain", 1765, "2026-05-26 12:00:00")
    assert _is_excluded(alarm, set(), set(), set()) is False
    assert _is_excluded(alarm, {"deep&dark web monitoring"}, {"stolen credentials"}, {"1272"}) is False


def test_is_excluded_handles_missing_type_details() -> None:
    alarm = _make_alarm()
    alarm["alarm_type_details"] = None
    assert _is_excluded(alarm, {"brand protection"}, {"x"}, {"1"}) is False


def _run_main(monkeypatch: pytest.MonkeyPatch, params: dict[str, str], alarms: list[dict[str, Any]],
              is_test_run: bool = True, last_run_ms: int = 0) -> MagicMock:
    siemplify = MagicMock()
    siemplify.extract_connector_param.side_effect = (
        lambda name, default_value=None, input_type=None: {"API Key": "k", "Company ID": "330", **params}.get(
            name, default_value
        )
    )
    siemplify.fetch_timestamp.return_value = last_run_ms
    siemplify.get_connector_context_property.return_value = ""
    siemplify.context.connector_info.environment = "Default Environment"
    manager = MagicMock()
    manager.get_all_incidents.return_value = (alarms, len(alarms))
    monkeypatch.setattr(mod, "SiemplifyConnectorExecution", lambda: siemplify)
    monkeypatch.setattr(mod, "SOCRadarManager", lambda *a, **k: manager)
    mod.main(is_test_run=is_test_run)
    return siemplify


def _returned_ids(siemplify: MagicMock) -> list[str]:
    return [a.display_id for a in siemplify.return_package.call_args.args[0]]


def test_main_drops_excluded_main_type_the_api_did_not_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    alarms = [
        _typed_alarm(1, "Deep&Dark Web Monitoring", "Stolen Credentials", 1272, "2026-05-26 12:00:00"),
        _typed_alarm(2, "Brand Protection", "Impersonating Domain", 1765, "2026-05-26 12:00:01"),
    ]
    siemplify = _run_main(monkeypatch, {"Excluded Main Type Filter": "Deep&Dark Web Monitoring"}, alarms)
    assert _returned_ids(siemplify) == ["2"]


def test_main_drops_excluded_sub_types_and_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    alarms = [
        _typed_alarm(1, "A", "Subdomain Takeover Check", 10, "2026-05-26 12:00:00"),
        _typed_alarm(2, "A", "Other", 20, "2026-05-26 12:00:01"),
        _typed_alarm(3, "A", "Kept", 30, "2026-05-26 12:00:02"),
    ]
    params = {"Excluded Sub Type Filter": "subdomain takeover check", "Excluded Alarm Type ID Filter": "20"}
    siemplify = _run_main(monkeypatch, params, alarms)
    assert _returned_ids(siemplify) == ["3"]


def test_main_without_exclusion_filters_keeps_every_alarm(monkeypatch: pytest.MonkeyPatch) -> None:
    alarms = [
        _typed_alarm(i, "Deep&Dark Web Monitoring", "Stolen Credentials", 1272, f"2026-05-26 12:00:0{i}")
        for i in range(1, 4)
    ]
    siemplify = _run_main(monkeypatch, {}, alarms)
    assert _returned_ids(siemplify) == ["1", "2", "3"]


def test_main_checkpoint_advances_past_excluded_alarms(monkeypatch: pytest.MonkeyPatch) -> None:
    alarms = [
        _typed_alarm(1, "A", "Kept", 30, "2026-05-26 12:00:00"),
        _typed_alarm(2, "A", "Noise", 10, "2026-05-26 12:05:00"),
    ]
    start_ms = int(datetime(2026, 5, 26, 11, 0, tzinfo=timezone.utc).timestamp() * 1000)
    siemplify = _run_main(
        monkeypatch, {"Excluded Sub Type Filter": "Noise"}, alarms, is_test_run=False, last_run_ms=start_ms
    )
    assert _returned_ids(siemplify) == ["1"]
    newest_ms = int(datetime(2026, 5, 26, 12, 5, tzinfo=timezone.utc).timestamp() * 1000)
    siemplify.save_timestamp.assert_called_once_with(new_timestamp=newest_ms + 1000)
