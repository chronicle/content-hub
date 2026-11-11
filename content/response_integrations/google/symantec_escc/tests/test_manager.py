from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest

from symantec_escc.core.SymantecESCCManager import SymantecESCCManager


def test_connectivity_success(symantec_manager: SymantecESCCManager) -> None:
    """Test successful connectivity to Symantec ESCC."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    symantec_manager.session.post.return_value = mock_response

    symantec_manager.test_connectivity()

    symantec_manager.session.post.assert_called_once()


def test_connectivity_failure_status_code(
    symantec_manager: SymantecESCCManager,
) -> None:
    """Test connectivity failure due to non-200 status code."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    symantec_manager.session.post.return_value = mock_response

    symantec_manager.test_connectivity()

    symantec_manager.session.post.assert_called_once()


def test_connectivity_request_exception(symantec_manager: SymantecESCCManager) -> None:
    """Test connectivity failure due to request exception."""
    symantec_manager.session.post.side_effect = Exception("Connection error")

    with pytest.raises(Exception):
        symantec_manager.test_connectivity()

    symantec_manager.session.post.assert_called_once()


@patch("symantec_escc.core.SymantecESCCManager.utc_now")
def test_connectivity_time_format(
    mock_utc_now, symantec_manager: SymantecESCCManager
) -> None:
    """Test the time formatting in connectivity request payload."""
    mock_datetime = datetime(2024, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)
    mock_utc_now.return_value = mock_datetime

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    symantec_manager.session.post.return_value = mock_response

    symantec_manager.test_connectivity()

    expected_time = "2024-01-01T12:00:00.123+00:00"
    symantec_manager.session.post.assert_called_once()
    actual_payload = symantec_manager.session.post.call_args[1]["json"]
    assert actual_payload["start_date"] == expected_time
    assert actual_payload["end_date"] == expected_time
