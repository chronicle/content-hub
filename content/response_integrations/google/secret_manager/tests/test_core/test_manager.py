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

"""Tests for SecretManagerClient."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import requests

from secret_manager.core.constants import DEFAULT_SECRET_VERSION
from secret_manager.core.exceptions import (
    ConnectivityError,
    InvalidConfigurationError,
    SecretAccessError,
)
from secret_manager.tests.core.factories import (
    make_client,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class _FixtureBridge:
    make_sa_json: Callable[..., str] | None = None


@pytest.fixture(autouse=True)
def _init_make_sa_json(make_sa_json: Callable[..., str]) -> None:
    _FixtureBridge.make_sa_json = make_sa_json


def make_sa_json(project_id: str = "test-project") -> str:
    if _FixtureBridge.make_sa_json is None:
        msg = "FixtureBridge.make_sa_json is not initialized"
        raise ValueError(msg)
    return _FixtureBridge.make_sa_json(project_id)

# -------------------------------------------------------------------
# Initialization
# -------------------------------------------------------------------


class TestClientInit:
    """Tests for SecretManagerClient.__init__."""

    def test_init_with_sa_json(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Client initializes with service account JSON."""
        sa_json: str = make_sa_json(project_id="my-project")

        client = make_client(
            service_account_json=sa_json,
            project_id="my-project",
        )

        assert client.project_id == "my-project"
        assert client.credentials is mock_sa_credentials

    def test_init_with_workload_identity(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Client initializes with workload identity email."""
        mock_creds: MagicMock = MagicMock()
        monkeypatch.setattr(
            "google.auth.default",
            lambda scopes: (mock_creds, None),
        )
        mock_impersonated: MagicMock = MagicMock()
        monkeypatch.setattr(
            "google.auth.impersonated_credentials.Credentials",
            lambda **kwargs: mock_impersonated,
        )

        client = make_client(
            workload_identity_email="sa@proj.iam.gserviceaccount.com",
            project_id="my-project",
        )

        assert client.project_id == "my-project"
        assert client.credentials is mock_impersonated

    def test_init_no_credentials_raises(self) -> None:
        """Raises InvalidConfigurationError when no auth provided."""
        with pytest.raises(InvalidConfigurationError, match="must be provided"):
            make_client()

    def test_init_no_project_id_raises(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Raises when project ID is missing and not in SA JSON."""
        sa_json: str = make_sa_json(project_id="")

        with pytest.raises(
            InvalidConfigurationError,
            match="Project ID must be provided",
        ):
            make_client(
                service_account_json=sa_json,
                project_id=None,
            )

    def test_init_invalid_json_raises(self) -> None:
        """Raises when service account JSON is malformed."""
        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid Service Account",
        ):
            make_client(
                service_account_json="not-valid-json{{{",
                project_id="my-project",
            )

    def test_verify_ssl_defaults_to_true(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """verify_ssl is True by default."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="my-project",
        )

        assert client.verify_ssl is True

    def test_verify_ssl_is_passed_to_session(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """When verify_ssl=False, create_authorized_session receives verify_ssl=False."""
        mock_session_instance = MagicMock()

        with patch(
            "secret_manager.core.manager.create_authorized_session",
            return_value=mock_session_instance,
        ) as mock_create_session:
            client = make_client(
                service_account_json=make_sa_json(),
                project_id="my-project",
                verify_ssl=False,
            )

        assert client.verify_ssl is False
        mock_create_session.assert_called_once_with(
            credentials=mock_sa_credentials,
            verify_ssl=False,
        )
        assert client._session is mock_session_instance


# -------------------------------------------------------------------
# Connectivity
# -------------------------------------------------------------------


class TestConnectivity:
    """Tests for test_connectivity."""

    def test_connectivity_success(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Connectivity succeeds using REST transport."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )
        with patch.object(client, "_rest_get") as mock_rest_get:
            mock_rest_get.return_value = {}
            result = client.test_connectivity()
            assert result is True
            mock_rest_get.assert_called_once_with(
                "projects/test-project/secrets",
                params={"pageSize": "1"},
            )

    def test_connectivity_failure_raises(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Raises ConnectivityError when REST call fails."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )
        with (
            patch.object(client, "_rest_get", side_effect=Exception("HTTP Error")),
            pytest.raises(ConnectivityError, match="HTTP Error"),
        ):
            client.test_connectivity()


# -------------------------------------------------------------------
# Secret Value Retrieval
# -------------------------------------------------------------------


class TestGetSecretValue:
    """Tests for get_secret_value."""

    def test_get_secret_value_success(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Returns decoded UTF-8 payload using REST transport."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )

        encoded_data = base64.b64encode(b"my-password-123").decode("utf-8")
        mock_response = {"payload": {"data": encoded_data}}

        with patch.object(client, "_rest_get", return_value=mock_response) as mock_rest_get:
            result = client.get_secret_value("db-password", "3")
            assert result == "my-password-123"
            mock_rest_get.assert_called_once_with("projects/test-project/secrets/db-password/versions/3:access")

    def test_get_secret_value_non_utf8_raises(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Raises SecretAccessError for binary / non-UTF-8 data."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )

        # b"\x80\x81\x82\xff" is invalid UTF-8
        encoded_data = base64.b64encode(b"\x80\x81\x82\xff").decode("utf-8")
        mock_response = {"payload": {"data": encoded_data}}

        with (
            patch.object(client, "_rest_get", return_value=mock_response),
            pytest.raises(SecretAccessError, match="non-UTF-8"),
        ):
            client.get_secret_value("binary-secret")

    def test_get_secret_value_api_error_raises(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Raises SecretAccessError when REST call fails."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )
        with (
            patch.object(client, "_rest_get", side_effect=Exception("HTTP Error")),
            pytest.raises(SecretAccessError, match="HTTP Error"),
        ):
            client.get_secret_value("db-password", "3")

    def test_get_secret_value_full_resource_name(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Uses full resource name path directly when secret_id starts with projects/."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )

        encoded_data = base64.b64encode(b"my-password-123").decode("utf-8")
        mock_response = {"payload": {"data": encoded_data}}

        with patch.object(client, "_rest_get", return_value=mock_response) as mock_rest_get:
            result = client.get_secret_value("projects/other-project/secrets/my-secret", "3")
            assert result == "my-password-123"
            mock_rest_get.assert_called_once_with("projects/other-project/secrets/my-secret/versions/3:access")


# -------------------------------------------------------------------
# Version Resolution
# -------------------------------------------------------------------


class TestResolveLatestEnabledVersion:
    """Tests for resolve_latest_enabled_version."""

    def test_picks_highest_version_number(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Selects the highest enabled version regardless of API order using REST."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )
        mock_response = {
            "versions": [
                {"name": "projects/test-project/secrets/my-secret/versions/3", "state": "ENABLED"},
                {"name": "projects/test-project/secrets/my-secret/versions/7", "state": "ENABLED"},
                {"name": "projects/test-project/secrets/my-secret/versions/1", "state": "ENABLED"},
                {"name": "projects/test-project/secrets/my-secret/versions/5", "state": "ENABLED"},
            ]
        }
        with patch.object(client, "_rest_get", return_value=mock_response) as mock_rest_get:
            result = client.resolve_latest_enabled_version("my-secret")
            assert result == "7"
            mock_rest_get.assert_called_once_with("projects/test-project/secrets/my-secret/versions")

    def test_picks_highest_version_number_with_full_resource_name(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Selects the highest enabled version using full resource name directly."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )
        mock_response = {
            "versions": [
                {"name": "projects/other-project/secrets/my-secret/versions/3", "state": "ENABLED"},
                {"name": "projects/other-project/secrets/my-secret/versions/7", "state": "ENABLED"},
            ]
        }
        with patch.object(client, "_rest_get", return_value=mock_response) as mock_rest_get:
            result = client.resolve_latest_enabled_version("projects/other-project/secrets/my-secret")
            assert result == "7"
            mock_rest_get.assert_called_once_with("projects/other-project/secrets/my-secret/versions")

    def test_skips_disabled_and_destroyed(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Only considers ENABLED versions using REST."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )
        mock_response = {
            "versions": [
                {"name": "projects/test-project/secrets/my-secret/versions/10", "state": "DESTROYED"},
                {"name": "projects/test-project/secrets/my-secret/versions/8", "state": "DISABLED"},
                {"name": "projects/test-project/secrets/my-secret/versions/5", "state": "ENABLED"},
                {"name": "projects/test-project/secrets/my-secret/versions/2", "state": "ENABLED"},
            ]
        }
        with patch.object(client, "_rest_get", return_value=mock_response):
            result = client.resolve_latest_enabled_version("my-secret")
            assert result == "5"

    def test_no_enabled_versions_returns_default(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Falls back to DEFAULT_SECRET_VERSION when none enabled."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )
        mock_response = {
            "versions": [
                {"name": "projects/test-project/secrets/my-secret/versions/1", "state": "DISABLED"},
                {"name": "projects/test-project/secrets/my-secret/versions/2", "state": "DESTROYED"},
            ]
        }
        with patch.object(client, "_rest_get", return_value=mock_response):
            result = client.resolve_latest_enabled_version("my-secret")
            assert result == DEFAULT_SECRET_VERSION

    def test_empty_list_returns_default(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Falls back when the secret has no versions at all."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )
        mock_response = {}
        with patch.object(client, "_rest_get", return_value=mock_response):
            result = client.resolve_latest_enabled_version("my-secret")
            assert result == DEFAULT_SECRET_VERSION

    def test_api_error_returns_default(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Falls back to DEFAULT on API failure instead of crashing using REST."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )
        with patch.object(client, "_rest_get", side_effect=Exception("HTTP Error")):
            result = client.resolve_latest_enabled_version("my-secret")
            assert result == DEFAULT_SECRET_VERSION


class TestRestGetErrorHandling:
    """Tests for _rest_get error validation and parsing."""

    def test_rest_get_success(self, mock_sa_credentials: MagicMock) -> None:
        """_rest_get returns parsed JSON response on success."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
            verify_ssl=False,
        )
        client._session = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"key": "value"}
        client._session.get.return_value = mock_response

        result = client._rest_get("some-path")
        assert result == {"key": "value"}
        mock_response.raise_for_status.assert_called_once()

    def test_rest_get_detailed_error_raising(self, mock_sa_credentials: MagicMock) -> None:
        """_rest_get raises HTTPError with detailed Google API error message."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
            verify_ssl=False,
        )
        client._session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 403

        original_error = requests.HTTPError("Original Forbidden Message", response=mock_response)
        mock_response.raise_for_status.side_effect = original_error

        mock_response.json.return_value = {
            "error": {"message": "Permission 'secretmanager.versions.access' denied on resource."}
        }
        client._session.get.return_value = mock_response

        with pytest.raises(requests.HTTPError) as exc_info:
            client._rest_get("some-path")

        assert "Permission 'secretmanager.versions.access' denied on resource. (HTTP 403)" in str(exc_info.value)
        assert exc_info.value.__cause__ is original_error

    def test_rest_get_generic_error_raising(self, mock_sa_credentials: MagicMock) -> None:
        """_rest_get raises original HTTPError if response is not valid JSON or lacks error message."""
        client = make_client(
            service_account_json=make_sa_json(),
            project_id="test-project",
            verify_ssl=False,
        )
        client._session = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500

        original_error = requests.HTTPError("Internal Server Error", response=mock_response)
        mock_response.raise_for_status.side_effect = original_error

        mock_response.json.side_effect = ValueError("Not JSON")
        client._session.get.return_value = mock_response

        with pytest.raises(requests.HTTPError) as exc_info:
            client._rest_get("some-path")

        assert str(exc_info.value) == "Internal Server Error"
