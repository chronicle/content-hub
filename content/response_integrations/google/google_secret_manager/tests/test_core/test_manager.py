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

"""Tests for GoogleSecretManagerClient."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from google.cloud import secretmanager

from google_secret_manager.core.constants import DEFAULT_SECRET_VERSION
from google_secret_manager.core.exceptions import (
    ConnectivityError,
    InvalidConfigurationError,
    SecretAccessError,
)
from google_secret_manager.core.manager import (
    GoogleSecretManagerClient,
)
from google_secret_manager.tests.core.factories import (
    make_access_response,
    make_sa_json,
    make_secret_version,
)

# -------------------------------------------------------------------
# Initialization
# -------------------------------------------------------------------


class TestClientInit:
    """Tests for GoogleSecretManagerClient.__init__."""

    def test_init_with_sa_json(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Client initializes with service account JSON."""
        sa_json: str = make_sa_json(project_id="my-project")

        client = GoogleSecretManagerClient(
            service_account_json=sa_json,
            project_id="my-project",
        )

        assert client.project_id == "my-project"
        assert client.credentials is mock_sa_credentials

    def test_init_with_workload_identity(
        self,
        mock_sm_service_client: MagicMock,
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

        client = GoogleSecretManagerClient(
            workload_identity_email="sa@proj.iam.gserviceaccount.com",
            project_id="my-project",
        )

        assert client.project_id == "my-project"
        assert client.credentials is mock_impersonated

    def test_init_no_credentials_raises(
        self,
        mock_sm_service_client: MagicMock,
    ) -> None:
        """Raises InvalidConfigurationError when no auth provided."""
        with pytest.raises(InvalidConfigurationError, match="must be provided"):
            GoogleSecretManagerClient()

    def test_init_no_project_id_raises(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Raises when project ID is missing and not in SA JSON."""
        sa_json: str = make_sa_json(project_id="")

        with pytest.raises(
            InvalidConfigurationError,
            match="Project ID must be provided",
        ):
            GoogleSecretManagerClient(
                service_account_json=sa_json,
                project_id=None,
            )

    def test_init_invalid_json_raises(
        self,
        mock_sm_service_client: MagicMock,
    ) -> None:
        """Raises when service account JSON is malformed."""
        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid Service Account",
        ):
            GoogleSecretManagerClient(
                service_account_json="not-valid-json{{{",
                project_id="my-project",
            )

    def test_verify_ssl_defaults_to_true(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """verify_ssl is True by default."""
        client = GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="my-project",
        )

        assert client.verify_ssl is True

    def test_verify_ssl_true_uses_grpc_transport(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """When verify_ssl=True (default), the standard gRPC transport is used."""
        GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="my-project",
            verify_ssl=True,
        )

        # Standard constructor call – no ``transport`` keyword.
        mock_sm_service_client_cls = (
            secretmanager.SecretManagerServiceClient
        )
        # The fixture patches the class; the class was called to produce the mock.
        # We verify the call did NOT include transport="rest".
        call_kwargs = mock_sm_service_client_cls.call_args
        if call_kwargs is not None:
            assert call_kwargs.kwargs.get("transport") != "rest"

    def test_verify_ssl_false_uses_direct_rest(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """When verify_ssl=False, direct AuthorizedSession is used with verify=False."""
        mock_session_instance = MagicMock()

        with patch(
            "google_secret_manager.core.manager.AuthorizedSession",
            return_value=mock_session_instance,
        ) as mock_auth_session_cls:
            client = GoogleSecretManagerClient(
                service_account_json=make_sa_json(),
                project_id="my-project",
                verify_ssl=False,
            )

        assert client.verify_ssl is False
        mock_auth_session_cls.assert_called_once_with(mock_sa_credentials)
        assert mock_session_instance.verify is False
        assert client._session is mock_session_instance
        assert client._service_client is None


# -------------------------------------------------------------------
# Connectivity
# -------------------------------------------------------------------


class TestConnectivity:
    """Tests for test_connectivity."""

    def test_connectivity_success(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Returns True when list_secrets succeeds."""
        mock_sm_service_client.list_secrets.return_value = iter([])
        sa_json: str = make_sa_json()

        client = GoogleSecretManagerClient(
            service_account_json=sa_json,
            project_id="test-project",
        )
        result: bool = client.test_connectivity()

        assert result is True
        mock_sm_service_client.list_secrets.assert_called_once()

    def test_connectivity_failure_raises(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Raises ConnectivityError when API call fails."""
        mock_sm_service_client.list_secrets.side_effect = Exception("Network error")
        sa_json: str = make_sa_json()

        client = GoogleSecretManagerClient(
            service_account_json=sa_json,
            project_id="test-project",
        )

        with pytest.raises(ConnectivityError, match="Network error"):
            client.test_connectivity()

    def test_connectivity_success_rest(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Connectivity succeeds using REST transport."""
        client = GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="test-project",
            verify_ssl=False,
        )
        with patch.object(client, "_rest_get") as mock_rest_get:
            mock_rest_get.return_value = {}
            result = client.test_connectivity()
            assert result is True
            mock_rest_get.assert_called_once_with(
                "projects/test-project/secrets",
                params={"pageSize": "1"},
            )

    def test_connectivity_failure_rest_raises(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Raises ConnectivityError when REST call fails."""
        client = GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="test-project",
            verify_ssl=False,
        )
        with patch.object(client, "_rest_get", side_effect=Exception("HTTP Error")):
            with pytest.raises(ConnectivityError, match="HTTP Error"):
                client.test_connectivity()


# -------------------------------------------------------------------
# Secret Value Retrieval
# -------------------------------------------------------------------


class TestGetSecretValue:
    """Tests for get_secret_value."""

    def _make_client(
        self,
        mock_sa_credentials: MagicMock,
    ) -> GoogleSecretManagerClient:
        return GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )

    def test_get_secret_value_success(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Returns decoded UTF-8 payload."""
        mock_sm_service_client.access_secret_version.return_value = make_access_response(
            b"my-password-123"
        )
        client = self._make_client(mock_sa_credentials)

        result: str = client.get_secret_value("db-password", "3")

        assert result == "my-password-123"

    def test_get_secret_value_non_utf8_raises(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Raises SecretAccessError for binary / non-UTF-8 data."""
        mock_sm_service_client.access_secret_version.return_value = make_access_response(
            b"\x80\x81\x82\xff"
        )
        client = self._make_client(mock_sa_credentials)

        with pytest.raises(SecretAccessError, match="non-UTF-8"):
            client.get_secret_value("binary-secret")

    def test_get_secret_value_api_error_raises(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Raises SecretAccessError when the API call fails."""
        mock_sm_service_client.access_secret_version.side_effect = Exception("Permission denied")
        client = self._make_client(mock_sa_credentials)

        with pytest.raises(
            SecretAccessError,
            match="Permission denied",
        ):
            client.get_secret_value("restricted-secret")

    def test_get_secret_value_success_rest(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Returns decoded UTF-8 payload using REST transport."""
        client = GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="test-project",
            verify_ssl=False,
        )
        import base64
        encoded_data = base64.b64encode(b"my-password-123").decode("utf-8")
        mock_response = {"payload": {"data": encoded_data}}

        with patch.object(client, "_rest_get", return_value=mock_response) as mock_rest_get:
            result = client.get_secret_value("db-password", "3")
            assert result == "my-password-123"
            mock_rest_get.assert_called_once_with(
                "projects/test-project/secrets/db-password/versions/3:access"
            )

    def test_get_secret_value_api_error_rest_raises(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Raises SecretAccessError when REST call fails."""
        client = GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="test-project",
            verify_ssl=False,
        )
        with patch.object(client, "_rest_get", side_effect=Exception("HTTP Error")):
            with pytest.raises(SecretAccessError, match="HTTP Error"):
                client.get_secret_value("db-password", "3")


# -------------------------------------------------------------------
# Version Resolution
# -------------------------------------------------------------------

_ENABLED = secretmanager.SecretVersion.State.ENABLED
_DISABLED = secretmanager.SecretVersion.State.DISABLED
_DESTROYED = secretmanager.SecretVersion.State.DESTROYED


class TestResolveLatestEnabledVersion:
    """Tests for resolve_latest_enabled_version."""

    def _make_client(
        self,
        mock_sa_credentials: MagicMock,
    ) -> GoogleSecretManagerClient:
        return GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="test-project",
        )

    def test_picks_highest_version_number(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Selects the highest enabled version regardless of API order."""
        versions = [
            make_secret_version(version_id="3", state=_ENABLED),
            make_secret_version(version_id="7", state=_ENABLED),
            make_secret_version(version_id="1", state=_ENABLED),
            make_secret_version(version_id="5", state=_ENABLED),
        ]
        mock_sm_service_client.list_secret_versions.return_value = iter(versions)
        client = self._make_client(mock_sa_credentials)

        result: str = client.resolve_latest_enabled_version("my-secret")

        assert result == "7"

    def test_skips_disabled_and_destroyed(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Only considers ENABLED versions."""
        versions = [
            make_secret_version(version_id="10", state=_DESTROYED),
            make_secret_version(version_id="8", state=_DISABLED),
            make_secret_version(version_id="5", state=_ENABLED),
            make_secret_version(version_id="2", state=_ENABLED),
        ]
        mock_sm_service_client.list_secret_versions.return_value = iter(versions)
        client = self._make_client(mock_sa_credentials)

        result: str = client.resolve_latest_enabled_version("my-secret")

        assert result == "5"

    def test_no_enabled_versions_returns_default(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Falls back to DEFAULT_SECRET_VERSION when none enabled."""
        versions = [
            make_secret_version(version_id="1", state=_DISABLED),
            make_secret_version(version_id="2", state=_DESTROYED),
        ]
        mock_sm_service_client.list_secret_versions.return_value = iter(versions)
        client = self._make_client(mock_sa_credentials)

        result: str = client.resolve_latest_enabled_version("my-secret")

        assert result == DEFAULT_SECRET_VERSION

    def test_empty_list_returns_default(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Falls back when the secret has no versions at all."""
        mock_sm_service_client.list_secret_versions.return_value = iter([])
        client = self._make_client(mock_sa_credentials)

        result: str = client.resolve_latest_enabled_version("my-secret")

        assert result == DEFAULT_SECRET_VERSION

    def test_api_error_returns_default(
        self,
        mock_sm_service_client: MagicMock,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Falls back to DEFAULT on API failure instead of crashing."""
        mock_sm_service_client.list_secret_versions.side_effect = Exception("Permission denied")
        client = self._make_client(mock_sa_credentials)

        result: str = client.resolve_latest_enabled_version("my-secret")

        assert result == DEFAULT_SECRET_VERSION

    def test_picks_highest_version_number_rest(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Selects the highest enabled version regardless of API order using REST."""
        client = GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="test-project",
            verify_ssl=False,
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
            mock_rest_get.assert_called_once_with(
                "projects/test-project/secrets/my-secret/versions"
            )

    def test_skips_disabled_and_destroyed_rest(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Only considers ENABLED versions using REST."""
        client = GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="test-project",
            verify_ssl=False,
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

    def test_api_error_returns_default_rest(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Falls back to DEFAULT on API failure instead of crashing using REST."""
        client = GoogleSecretManagerClient(
            service_account_json=make_sa_json(),
            project_id="test-project",
            verify_ssl=False,
        )
        with patch.object(client, "_rest_get", side_effect=Exception("HTTP Error")):
            result = client.resolve_latest_enabled_version("my-secret")
            assert result == DEFAULT_SECRET_VERSION
