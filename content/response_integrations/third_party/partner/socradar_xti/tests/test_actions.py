"""Unit tests for SOCRadar actions."""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _make_siemplify_mock(config: dict[str, Any] | None = None, params: dict[str, Any] | None = None) -> MagicMock:
    """Create a mock SiemplifyAction with configuration and action params."""
    siemplify = MagicMock()
    siemplify.script_name = "test"

    default_config = {
        "API Root": "https://platform.socradar.com/api",
        "API Key": "test-key",
        "Company ID": "12345",
        "Verify SSL": True,
        "IOC Enrichment API Key": "test-ioc-key",
        "Rapid Reputation API Key": "test-rapid-key",
    }
    if config:
        default_config.update(config)

    def extract_config(integration: str, param: str, **kwargs: Any) -> Any:
        return default_config.get(param, kwargs.get("default_value"))

    def extract_param(param: str, **kwargs: Any) -> Any:
        p = params or {}
        return p.get(param, kwargs.get("default_value"))

    siemplify.extract_configuration_param = extract_config
    siemplify.extract_action_param = extract_param
    siemplify.result = MagicMock()
    return siemplify


# -- Ping --


@patch("soar_sdk.SiemplifyAction.SiemplifyAction")
def test_ping_success(mock_cls: MagicMock) -> None:
    siemplify = _make_siemplify_mock()
    mock_cls.return_value = siemplify

    with patch("socradar_xti.core.SOCRadarManager.SOCRadarManager") as MockMgr:
        instance = MockMgr.return_value
        instance.test_connectivity.return_value = True

        from socradar_xti.actions.Ping import main
        main()

        siemplify.end.assert_called_once()
        call_args = siemplify.end.call_args[0]
        assert "Successfully connected" in call_args[0]
        assert call_args[1] is True


@patch("soar_sdk.SiemplifyAction.SiemplifyAction")
def test_ping_failure(mock_cls: MagicMock) -> None:
    siemplify = _make_siemplify_mock()
    mock_cls.return_value = siemplify

    with patch("socradar_xti.core.SOCRadarManager.SOCRadarManager") as MockMgr:
        instance = MockMgr.return_value
        instance.test_connectivity.side_effect = Exception("Connection refused")

        from socradar_xti.actions.Ping import main
        main()

        call_args = siemplify.end.call_args[0]
        assert "Failed to connect" in call_args[0]
        assert call_args[1] is False


# -- GetAlarmDetails --


@patch("soar_sdk.SiemplifyAction.SiemplifyAction")
def test_get_alarm_details_success(mock_cls: MagicMock) -> None:
    siemplify = _make_siemplify_mock(params={"Alarm ID": "12345"})
    mock_cls.return_value = siemplify

    alarm = {"alarm_id": 12345, "alarm_type_details": {"alarm_generic_title": "Test Alarm"}}

    with patch("socradar_xti.core.SOCRadarManager.SOCRadarManager") as MockMgr:
        instance = MockMgr.return_value
        instance.get_alarm_details.return_value = alarm

        from socradar_xti.actions.GetAlarmDetails import main
        main()

        siemplify.result.add_result_json.assert_called_once_with(alarm)
        call_args = siemplify.end.call_args[0]
        assert call_args[1] is True


@patch("soar_sdk.SiemplifyAction.SiemplifyAction")
def test_get_alarm_details_not_found(mock_cls: MagicMock) -> None:
    siemplify = _make_siemplify_mock(params={"Alarm ID": "99999"})
    mock_cls.return_value = siemplify

    with patch("socradar_xti.core.SOCRadarManager.SOCRadarManager") as MockMgr:
        from socradar_xti.core.SOCRadarManager import SOCRadarManagerError
        instance = MockMgr.return_value
        instance.get_alarm_details.side_effect = SOCRadarManagerError("Not found")

        from socradar_xti.actions.GetAlarmDetails import main
        main()

        call_args = siemplify.end.call_args[0]
        assert call_args[1] is False


# -- EnrichIndicator --


@patch("soar_sdk.SiemplifyAction.SiemplifyAction")
def test_enrich_indicator_success(mock_cls: MagicMock) -> None:
    siemplify = _make_siemplify_mock(params={
        "Indicator": "8.8.8.8",
        "Include AI Insight": "false",
        "Fields": "",
    })
    mock_cls.return_value = siemplify

    result = {
        "details": {"score": [27.5], "feed_source_list": [{"source": "test"}]},
        "categorization": {"malware": False},
        "api_credit": {"remaining_credit": 100},
    }

    with patch("socradar_xti.core.SOCRadarManager.SOCRadarManager") as MockMgr:
        instance = MockMgr.return_value
        instance.enrich_indicator.return_value = result

        from socradar_xti.actions.EnrichIndicator import main
        main()

        siemplify.result.add_result_json.assert_called_once()
        call_args = siemplify.end.call_args[0]
        assert call_args[1] is True  # has results


@patch("soar_sdk.SiemplifyAction.SiemplifyAction")
def test_enrich_indicator_no_key(mock_cls: MagicMock) -> None:
    siemplify = _make_siemplify_mock(config={"IOC Enrichment API Key": ""}, params={
        "Indicator": "8.8.8.8",
        "Include AI Insight": "false",
        "Fields": "",
    })
    mock_cls.return_value = siemplify

    from socradar_xti.actions.EnrichIndicator import main
    main()

    call_args = siemplify.end.call_args[0]
    assert "not configured" in call_args[0]
    assert call_args[1] is False


# -- RapidReputation --


@patch("soar_sdk.SiemplifyAction.SiemplifyAction")
def test_rapid_reputation_success(mock_cls: MagicMock) -> None:
    siemplify = _make_siemplify_mock(params={
        "Entity Value": "1.2.3.4",
        "Entity Type": "ip",
    })
    mock_cls.return_value = siemplify

    result = {
        "data": {"score": 54.3, "is_whitelisted": False, "finding_sources": [{"source": "test"}]},
        "is_success": True,
    }

    with patch("socradar_xti.core.SOCRadarManager.SOCRadarManager") as MockMgr:
        instance = MockMgr.return_value
        instance.rapid_reputation.return_value = result

        from socradar_xti.actions.RapidReputation import main
        main()

        call_args = siemplify.end.call_args[0]
        assert call_args[1] is True


@patch("soar_sdk.SiemplifyAction.SiemplifyAction")
def test_rapid_reputation_invalid_type(mock_cls: MagicMock) -> None:
    siemplify = _make_siemplify_mock(params={
        "Entity Value": "1.2.3.4",
        "Entity Type": "invalid",
    })
    mock_cls.return_value = siemplify

    from socradar_xti.actions.RapidReputation import main
    main()

    call_args = siemplify.end.call_args[0]
    assert "Invalid entity type" in call_args[0]
    assert call_args[1] is False
