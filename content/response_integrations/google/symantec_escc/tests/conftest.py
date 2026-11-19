# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest
import soar_sdk  # noqa: F401
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
