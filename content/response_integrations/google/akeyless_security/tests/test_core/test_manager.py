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
from akeyless.exceptions import ApiException

from akeyless_security.core.constants import DEFAULT_MAX_RETRIES
from akeyless_security.core.datamodels import AkeylessClientConfig
from akeyless_security.core.exceptions import (
    AkeylessError,
    ConnectivityError,
    InvalidConfigurationError,
    SecretAccessError,
)
from akeyless_security.core.manager import AkeylessClient
from akeyless_security.core.utils import validate_response


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
        assert client.configuration.retries == DEFAULT_MAX_RETRIES

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
        assert client.configuration.assert_hostname is False

    def test_init_reads_proxy_from_env(
        self,
        mock_akeyless_api: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Client configures configuration.proxy when https_proxy is set in os.environ."""
        monkeypatch.setenv("https_proxy", "http://127.0.0.1:8080")
        config = AkeylessClientConfig(
            access_id="test-access-id",
            access_key="test-access-key",
            verify_ssl=False,
        )
        client = AkeylessClient(config)
        assert client.configuration.proxy == "http://127.0.0.1:8080"

    def test_init_missing_access_id_raises(self, mock_akeyless_api: MagicMock) -> None:
        """Raises InvalidConfigurationError when access_id is missing."""
        config = AkeylessClientConfig(access_id="", access_key="test-access-key")
        with pytest.raises(
            InvalidConfigurationError,
            match="Both Access ID and Access Key must be provided",
        ):
            AkeylessClient(config)

    def test_init_missing_access_key_raises(self, mock_akeyless_api: MagicMock) -> None:
        """Raises InvalidConfigurationError when access_key is missing."""
        config = AkeylessClientConfig(access_id="test-access-id", access_key="")
        with pytest.raises(
            InvalidConfigurationError,
            match="Both Access ID and Access Key must be provided",
        ):
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

    def test_get_token_empty_token_raises(self, mock_akeyless_api: MagicMock) -> None:
        """get_token raises ConnectivityError when auth returns an empty token."""
        mock_auth_res = MagicMock()
        mock_auth_res.token = ""
        mock_akeyless_api.auth.return_value = mock_auth_res

        config = AkeylessClientConfig(access_id="test-access-id", access_key="test-access-key")
        client = AkeylessClient(config)
        with pytest.raises(ConnectivityError, match="no token was returned"):
            client.get_token()

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
        with pytest.raises(ConnectivityError, match="Invalid credentials"):
            client.test_connectivity()

    def test_test_connectivity_invalid_access_id_strips_headers(
        self, mock_akeyless_api: MagicMock
    ) -> None:
        """test_connectivity parses 401 JSON error body and omits HTTP headers."""
        mock_resp = MagicMock()
        mock_resp.status = 401
        mock_resp.reason = "Unauthorized"
        mock_resp.data = (
            '{"error":"failed to get credentials: Desc: Failed to authenticate API key access."}'
        )
        mock_resp.getheaders.return_value = {
            "Content-Security-Policy": "very-long-header-value",
            "Content-Type": "application/json",
        }
        mock_akeyless_api.auth.side_effect = ApiException(http_resp=mock_resp)

        config = AkeylessClientConfig(access_id="p-invalid", access_key="test-access-key")
        client = AkeylessClient(config)
        with pytest.raises(ConnectivityError) as exc_info:
            client.test_connectivity()

        err_msg = str(exc_info.value)
        assert "(401) Unauthorized" in err_msg
        assert "failed to get credentials: Desc: Failed to authenticate API key access." in err_msg
        assert "HTTP response headers" not in err_msg
        assert "Content-Security-Policy" not in err_msg

    def test_test_connectivity_invalid_access_key_strips_headers(
        self, mock_akeyless_api: MagicMock
    ) -> None:
        """test_connectivity parses 400 JSON error body and omits HTTP headers."""
        mock_resp = MagicMock()
        mock_resp.status = 400
        mock_resp.reason = "Bad Request"
        mock_resp.data = (
            '{"error":"Error: failed to decode api key. error: illegal base64 data at input byte 0"}'
        )
        mock_resp.getheaders.return_value = {
            "Content-Security-Policy": "very-long-header-value",
        }
        mock_akeyless_api.auth.side_effect = ApiException(http_resp=mock_resp)

        config = AkeylessClientConfig(access_id="p-valid", access_key="invalid-key")
        client = AkeylessClient(config)
        with pytest.raises(ConnectivityError) as exc_info:
            client.test_connectivity()

        err_msg = str(exc_info.value)
        assert "(400) Bad Request" in err_msg
        assert "Error: failed to decode api key. error: illegal base64 data at input byte 0" in err_msg
        assert "HTTP response headers" not in err_msg
        assert "Content-Security-Policy" not in err_msg

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

    def test_get_secret_value_invalid_version_raises(self, mock_akeyless_api: MagicMock) -> None:
        """get_secret_value raises InvalidConfigurationError when version_id is not a positive integer."""
        mock_auth_res = MagicMock()
        mock_auth_res.token = "test-token"
        mock_akeyless_api.auth.return_value = mock_auth_res

        config = AkeylessClientConfig(access_id="test-access-id", access_key="test-access-key")
        client = AkeylessClient(config)
        with pytest.raises(InvalidConfigurationError, match="Invalid version '::::2'"):
            client.get_secret_value("my-secret", version_id="::::2")


class TestValidateResponse:
    """Tests for validate_response utility."""

    def test_validate_response_200_ok(self) -> None:
        """validate_response does not raise for 2xx HTTP status."""
        mock_resp = MagicMock(status=200, reason="OK", data=b'{"token":"abc"}')
        validate_response(mock_resp)

    def test_validate_response_http_response_error_json(self) -> None:
        """validate_response extracts error from non-2xx HTTP response JSON body."""
        mock_resp = MagicMock(
            status=400,
            reason="Bad Request",
            data=b'{"error":"Error: failed to decode api key."}',
        )
        with pytest.raises(AkeylessError) as exc_info:
            validate_response(mock_resp, error_msg="Auth failed")

        assert str(exc_info.value) == (
            "Auth failed: (400) Bad Request - Error: failed to decode api key."
        )
