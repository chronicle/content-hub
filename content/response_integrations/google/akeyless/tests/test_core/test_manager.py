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

"""Tests for AkeylessClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from akeyless.core.manager import AkeylessClient
from akeyless.core.constants import DEFAULT_SECRET_VERSION
from akeyless.core.exceptions import (
    ConnectivityError,
    InvalidConfigurationError,
    SecretAccessError,
)


class TestAkeylessClient:
    """Tests for AkeylessClient."""

    def test_init_success(self, mock_akeyless_api: MagicMock) -> None:
        """Client initializes successfully with valid credentials."""
        client = AkeylessClient(access_id="test-access-id", access_key="test-access-key")
        assert client.access_id == "test-access-id"
        assert client.access_key == "test-access-key"

    def test_init_missing_access_id_raises(self, mock_akeyless_api: MagicMock) -> None:
        """Raises InvalidConfigurationError when access_id is missing."""
        with pytest.raises(InvalidConfigurationError, match="Access ID must be provided"):
            AkeylessClient(access_id="")

    def test_test_connectivity_success(self, mock_akeyless_api: MagicMock) -> None:
        """test_connectivity returns True on successful auth."""
        mock_auth_res = MagicMock()
        mock_auth_res.token = "test-token"
        mock_akeyless_api.auth.return_value = mock_auth_res

        client = AkeylessClient(access_id="test-access-id", access_key="test-access-key")
        assert client.test_connectivity() is True
        mock_akeyless_api.auth.assert_called_once()

    def test_test_connectivity_failure(self, mock_akeyless_api: MagicMock) -> None:
        """test_connectivity raises ConnectivityError on API error."""
        mock_akeyless_api.auth.side_effect = Exception("Invalid credentials")

        client = AkeylessClient(access_id="test-access-id", access_key="test-access-key")
        with pytest.raises(ConnectivityError, match="Failed to connect to Akeyless"):
            client.test_connectivity()

    def test_get_secret_value_success(self, mock_akeyless_api: MagicMock) -> None:
        """get_secret_value returns secret string successfully."""
        mock_auth_res = MagicMock()
        mock_auth_res.token = "test-token"
        mock_akeyless_api.auth.return_value = mock_auth_res

        mock_akeyless_api.get_secret_value.return_value = {"my-secret": "super-secret-payload"}

        client = AkeylessClient(access_id="test-access-id", access_key="test-access-key")
        result = client.get_secret_value("my-secret")
        assert result == "super-secret-payload"

    def test_get_secret_value_missing_raises(self, mock_akeyless_api: MagicMock) -> None:
        """get_secret_value raises SecretAccessError when secret is missing in response."""
        mock_auth_res = MagicMock()
        mock_auth_res.token = "test-token"
        mock_akeyless_api.auth.return_value = mock_auth_res

        mock_akeyless_api.get_secret_value.return_value = {}

        client = AkeylessClient(access_id="test-access-id", access_key="test-access-key")
        with pytest.raises(SecretAccessError, match="not found in Akeyless response"):
            client.get_secret_value("my-secret")

    @patch("akeyless.core.manager.AkeylessClient._fetch_gcp_id_token")
    def test_gcp_auth_success(self, mock_fetch_gcp: MagicMock, mock_akeyless_api: MagicMock) -> None:
        """GCP authentication succeeds when metadata server provides ID token."""
        mock_fetch_gcp.return_value = "mock-gcp-id-token"
        mock_auth_res = MagicMock()
        mock_auth_res.token = "gcp-session-token"
        mock_akeyless_api.auth.return_value = mock_auth_res

        client = AkeylessClient(access_id="test-access-id", access_type="gcp")
        token = client.get_token()

        assert token == "gcp-session-token"
        mock_fetch_gcp.assert_called_once_with("test-access-id")
        mock_akeyless_api.auth.assert_called_once()

    @patch("akeyless.core.manager.AkeylessClient._fetch_gcp_id_token")
    def test_gcp_auth_fallback_to_access_key(self, mock_fetch_gcp: MagicMock, mock_akeyless_api: MagicMock) -> None:
        """Falls back to access_key auth when GCP metadata server is not reachable but access_key is provided."""
        mock_fetch_gcp.side_effect = Exception("Metadata server not reachable")
        mock_auth_res = MagicMock()
        mock_auth_res.token = "fallback-access-key-token"
        mock_akeyless_api.auth.return_value = mock_auth_res

        client = AkeylessClient(
            access_id="test-access-id",
            access_key="test-access-key",
            access_type="gcp"
        )
        token = client.get_token()

        assert token == "fallback-access-key-token"
        mock_fetch_gcp.assert_called_once()
        mock_akeyless_api.auth.assert_called_once()

    @patch("akeyless.core.manager.AkeylessClient._fetch_gcp_id_token")
    def test_gcp_auth_no_access_key_raises(self, mock_fetch_gcp: MagicMock, mock_akeyless_api: MagicMock) -> None:
        """Raises ConnectivityError when GCP authentication fails and no access_key is provided."""
        mock_fetch_gcp.side_effect = Exception("Metadata server not reachable")

        client = AkeylessClient(
            access_id="test-access-id",
            access_key=None,
            access_type="gcp"
        )
        with pytest.raises(ConnectivityError, match="Failed to authenticate with Akeyless using GCP IAM"):
            client.get_token()
