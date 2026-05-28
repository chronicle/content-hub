"""Unit tests for SOCRadarManager."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ..core.SOCRadarManager import (
    STATUS_CODES,
    VALID_SEVERITIES,
    SOCRadarManager,
    SOCRadarManagerError,
)


@pytest.fixture
def manager() -> SOCRadarManager:
    return SOCRadarManager(
        api_root="https://platform.socradar.com/api",
        api_key="test-api-key",
        company_id="12345",
        verify_ssl=False,
    )


# -- Connectivity --


def test_test_connectivity_success(manager: SOCRadarManager) -> None:
    with patch.object(manager, "_request", return_value={"is_success": True}):
        assert manager.test_connectivity() is True


def test_test_connectivity_failure(manager: SOCRadarManager) -> None:
    with patch.object(manager, "_request", side_effect=SOCRadarManagerError("Unauthorized")):
        with pytest.raises(SOCRadarManagerError, match="Unauthorized"):
            manager.test_connectivity()


# -- _extract_alarms_data --


def test_extract_alarms_flat_list() -> None:
    response = {"data": [{"alarm_id": 1}, {"alarm_id": 2}]}
    alarms, total, pages = SOCRadarManager._extract_alarms_data(response)
    assert len(alarms) == 2
    assert total == 2
    assert pages == 1


def test_extract_alarms_nested_dict() -> None:
    response = {"data": {"alarms": [{"alarm_id": 1}], "total_records": 50, "total_pages": 5}}
    alarms, total, pages = SOCRadarManager._extract_alarms_data(response)
    assert len(alarms) == 1
    assert total == 50
    assert pages == 5


def test_extract_alarms_empty() -> None:
    response = {"data": []}
    alarms, total, pages = SOCRadarManager._extract_alarms_data(response)
    assert alarms == []
    assert total == 0


def test_extract_alarms_unexpected_type() -> None:
    response = {"data": "unexpected"}
    alarms, total, pages = SOCRadarManager._extract_alarms_data(response)
    assert alarms == []
    assert total == 0


# -- get_alarm_details --


def test_get_alarm_details_found(manager: SOCRadarManager) -> None:
    mock_response = {"data": [{"alarm_id": 999, "status": "OPEN"}]}
    with patch.object(manager, "get_incidents_page", return_value=mock_response):
        result = manager.get_alarm_details(999)
        assert result["alarm_id"] == 999


def test_get_alarm_details_not_found(manager: SOCRadarManager) -> None:
    mock_response = {"data": []}
    with patch.object(manager, "get_incidents_page", return_value=mock_response):
        with pytest.raises(SOCRadarManagerError, match="not found"):
            manager.get_alarm_details(999)


# -- change_status --


def test_change_status_valid_name(manager: SOCRadarManager) -> None:
    with patch.object(manager, "_request", return_value={"is_success": True}) as mock:
        manager.change_status(123, "INVESTIGATING")
        call_body = mock.call_args[0][2]
        assert call_body["status"] == 1
        assert call_body["alarm_ids"] == ["123"]


def test_change_status_invalid_name(manager: SOCRadarManager) -> None:
    with pytest.raises(SOCRadarManagerError, match="Invalid status"):
        manager.change_status(123, "INVALID_STATUS")


def test_change_status_integer(manager: SOCRadarManager) -> None:
    with patch.object(manager, "_request", return_value={"is_success": True}) as mock:
        manager.change_status(123, 2)
        call_body = mock.call_args[0][2]
        assert call_body["status"] == 2


# -- change_severity --


def test_change_severity_valid(manager: SOCRadarManager) -> None:
    with patch.object(manager, "_request", return_value={"is_success": True}):
        manager.change_severity(123, "HIGH")


def test_change_severity_invalid(manager: SOCRadarManager) -> None:
    with pytest.raises(SOCRadarManagerError, match="Invalid severity"):
        manager.change_severity(123, "SUPER_HIGH")


def test_change_severity_non_string(manager: SOCRadarManager) -> None:
    with pytest.raises(SOCRadarManagerError, match="Severity must be a string"):
        manager.change_severity(123, 42)


# -- add_comment --


def test_add_comment(manager: SOCRadarManager) -> None:
    with patch.object(manager, "_request", return_value={"is_success": True}) as mock:
        manager.add_comment(123, "test comment", "user@test.com")
        call_body = mock.call_args[0][2]
        assert call_body["alarm_id"] == 123
        assert call_body["comment"] == "test comment"
        assert call_body["user_email"] == "user@test.com"


# -- add_tag / remove_tag --


def test_add_tag(manager: SOCRadarManager) -> None:
    with patch.object(manager, "get_alarm_details", return_value={"tags": []}):
        with patch.object(manager, "_request", return_value={"is_success": True}) as mock:
            manager.add_tag(123, "test-tag")
            call_body = mock.call_args[0][2]
            assert call_body["tag"] == "test-tag"


def test_add_tag_already_present(manager: SOCRadarManager) -> None:
    with patch.object(manager, "get_alarm_details", return_value={"tags": ["test-tag"]}):
        result = manager.add_tag(123, "test-tag")
        assert result["is_success"] is True
        assert "already present" in result["message"]


def test_remove_tag(manager: SOCRadarManager) -> None:
    with patch.object(manager, "get_alarm_details", return_value={"tags": ["test-tag"]}):
        with patch.object(manager, "_request", return_value={"is_success": True}) as mock:
            manager.remove_tag(123, "test-tag")
            call_body = mock.call_args[0][2]
            assert call_body["tag"] == "test-tag"


def test_remove_tag_not_present(manager: SOCRadarManager) -> None:
    with patch.object(manager, "get_alarm_details", return_value={"tags": []}):
        result = manager.remove_tag(123, "test-tag")
        assert result["is_success"] is True
        assert "not present" in result["message"]


# -- change_assignee --


def test_change_assignee_emails(manager: SOCRadarManager) -> None:
    with patch.object(manager, "_request", return_value={"is_success": True}) as mock:
        manager.change_assignee(123, user_emails=["a@b.com"])
        call_body = mock.call_args[0][2]
        assert call_body["user_emails"] == ["a@b.com"]


def test_change_assignee_no_args(manager: SOCRadarManager) -> None:
    with pytest.raises(SOCRadarManagerError, match="At least"):
        manager.change_assignee(123)


# -- IOC Feed --


def test_get_ioc_feed(manager: SOCRadarManager) -> None:
    mock_data = [{"feed": "1.2.3.4", "feed_type": "ip"}]
    with patch.object(manager.session, "get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_data
        mock_get.return_value = mock_resp
        result = manager.get_ioc_feed("test-uuid")
        assert len(result) == 1
        assert result[0]["feed_type"] == "ip"


def test_get_multiple_ioc_feeds(manager: SOCRadarManager) -> None:
    with patch.object(manager, "get_ioc_feed") as mock:
        mock.side_effect = [
            [{"feed": "1.2.3.4"}],
            SOCRadarManagerError("not found"),
        ]
        results = manager.get_multiple_ioc_feeds(["uuid1", "uuid2"])
        assert isinstance(results["uuid1"], list)
        assert "error" in results["uuid2"]


# -- Constants --


def test_status_codes_completeness() -> None:
    assert len(STATUS_CODES) == 11
    assert STATUS_CODES["OPEN"] == 0
    assert STATUS_CODES["FALSE_POSITIVE"] == 9


def test_valid_severities() -> None:
    assert "CRITICAL" in VALID_SEVERITIES
    assert "LOW" in VALID_SEVERITIES
    assert len(VALID_SEVERITIES) == 4
