from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest
from symantec_escc.core.SymantecESCCManager import SymantecESCCManager


@pytest.fixture(name="mock_token_response_fixture")
def mock_token_response():
    """
    Fixture that mocks the token generation response.
    Returns a mock requests object with a successful token response.
    """
    with patch(
        "symantec_escc.core.SymantecESCCManager.requests"
    ) as mock_requests:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token"}
        mock_requests.post.return_value = mock_response
        yield mock_requests


@pytest.fixture
def symantec_manager(mock_token_response_fixture) -> SymantecESCCManager:
    """
    Fixture that returns a configured SymantecESCCManager instance.
    The manager is initialized with test values and mocked session.

    Args:
        mock_token_response: Fixture that mocks the token generation request
    """
    manager = SymantecESCCManager(
        api_root="https://test.symantec.com/api",
        client_id="test_client_id",
        client_secret="test_client_secret",
    )
    # Clear any previous mock calls after initialization
    mock_token_response_fixture.reset_mock()

    manager.session.post = MagicMock()
    return manager
