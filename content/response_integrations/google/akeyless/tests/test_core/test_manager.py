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

# ruff:file-ignore[hardcoded-password-string]
from unittest.mock import MagicMock

import pytest

from akeyless.core.exceptions import (
    ConnectivityError,
    InvalidConfigurationError,
    SecretAccessError,
)
from akeyless.core.manager import AkeylessClient, AkeylessClientConfig


class TestAkeylessClient:
    """Tests for AkeylessClient."""

    def test_init_success(self, mock_akeyless_api: MagicMock) -> None:
        """Client initializes successfully with valid credentials."""
        config = AkeylessClientConfig(access_id="test-access-id", access_key="test-access-key")
        client = AkeylessClient(config)
        assert client.config.access_id == "test-access-id"
        assert client.config.access_key == "test-access-key"
        assert client.config.verify_ssl is True
        assert client.configuration.verify_ssl is True

    def test_init_explicit_verify_ssl_false(self, mock_akeyless_api: MagicMock) -> None:
        """Client initializes successfully with verify_ssl set to False."""
        config = AkeylessClientConfig(
            access_id="test-access-id",
            access_key="test-access-key",
            verify_ssl=False,
        )
        client = AkeylessClient(config)
        assert client.config.verify_ssl is False
        assert client.configuration.verify_ssl is False

    def test_init_missing_access_id_raises(self, mock_akeyless_api: MagicMock) -> None:
        """Raises InvalidConfigurationError when access_id is missing."""
        config = AkeylessClientConfig(access_id="", access_key="test-access-key")
        with pytest.raises(InvalidConfigurationError, match="Access ID must be provided"):
            AkeylessClient(config)

    def test_init_missing_access_key_raises(self, mock_akeyless_api: MagicMock) -> None:
        """Raises InvalidConfigurationError when access_key is missing."""
        config = AkeylessClientConfig(access_id="test-access-id", access_key="")
        with pytest.raises(InvalidConfigurationError, match="Access Key must be provided"):
            AkeylessClient(config)

    def test_get_token_success(self, mock_akeyless_api: MagicMock) -> None:
        """get_token returns token on successful auth and caches it."""
        mock_auth_res = MagicMock()
        mock_auth_res.token = "test-token"
        mock_akeyless_api.auth.return_value = mock_auth_res

        config = AkeylessClientConfig(access_id="test-access-id", access_key="test-access-key")
        client = AkeylessClient(config)
        token = client.get_token()

        assert token == "test-token"
        mock_akeyless_api.auth.assert_called_once()

        # Second call uses cache
        token2 = client.get_token()
        assert token2 == "test-token"
        mock_akeyless_api.auth.assert_called_once()

    def test_test_connectivity_success(self, mock_akeyless_api: MagicMock) -> None:
        """test_connectivity returns True on successful auth."""
        mock_auth_res = MagicMock()
        mock_auth_res.token = "test-token"
        mock_akeyless_api.auth.return_value = mock_auth_res

        config = AkeylessClientConfig(access_id="test-access-id", access_key="test-access-key")
        client = AkeylessClient(config)
        assert client.test_connectivity() is True
        mock_akeyless_api.auth.assert_called_once()

    def test_test_connectivity_failure(self, mock_akeyless_api: MagicMock) -> None:
        """test_connectivity raises ConnectivityError on API error."""
        mock_akeyless_api.auth.side_effect = Exception("Invalid credentials")

        config = AkeylessClientConfig(access_id="test-access-id", access_key="test-access-key")
        client = AkeylessClient(config)
        with pytest.raises(ConnectivityError, match="Failed to connect to Akeyless"):
            client.test_connectivity()

    def test_get_secret_value_success(self, mock_akeyless_api: MagicMock) -> None:
        """get_secret_value returns secret string successfully."""
        mock_auth_res = MagicMock()
        mock_auth_res.token = "test-token"
        mock_akeyless_api.auth.return_value = mock_auth_res

        mock_akeyless_api.get_secret_value.return_value = {"my-secret": "super-secret-payload"}

        config = AkeylessClientConfig(access_id="test-access-id", access_key="test-access-key")
        client = AkeylessClient(config)
        result = client.get_secret_value("my-secret")
        assert result == "super-secret-payload"

    def test_get_secret_value_missing_raises(self, mock_akeyless_api: MagicMock) -> None:
        """get_secret_value raises SecretAccessError when secret is missing in response."""
        mock_auth_res = MagicMock()
        mock_auth_res.token = "test-token"
        mock_akeyless_api.auth.return_value = mock_auth_res

        mock_akeyless_api.get_secret_value.return_value = {}

        config = AkeylessClientConfig(access_id="test-access-id", access_key="test-access-key")
        client = AkeylessClient(config)
        with pytest.raises(SecretAccessError, match="not found in Akeyless response"):
            client.get_secret_value("my-secret")
