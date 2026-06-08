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

"""Tests for authentication."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import google.auth.exceptions
import pytest

from google_secret_manager.core.authentication import (
    IntegrationParameters,
    _get_credentials_using_service_account,
    _get_credentials_using_workload_identity_email,
    build_auth_params,
    create_authorized_session,
    get_credentials,
    prepare_auth_request,
)
from google_secret_manager.core.constants import (
    INTEGRATION_IDENTIFIER,
    PROJECT_ID_PARAM,
    SERVICE_ACCOUNT_JSON_PARAM,
    VERIFY_SSL_PARAM,
    WORKLOAD_IDENTITY_EMAIL_PARAM,
)
from google_secret_manager.core.exceptions import (
    GoogleSecretManagerError,
    InvalidConfigurationError,
)
from google_secret_manager.tests.core.factories import (
    make_sa_json,
)


class TestBuildAuthParams:
    """Tests for the build_auth_params factory function."""

    def test_action_extracts_from_configuration(self) -> None:
        """For SiemplifyAction, reads from get_configuration()."""
        mock_action: MagicMock = MagicMock()
        mock_action.__class__.__name__ = "SiemplifyAction"
        mock_action.get_configuration.return_value = {
            SERVICE_ACCOUNT_JSON_PARAM: "sa-json-value",
            PROJECT_ID_PARAM: "proj-123",
            WORKLOAD_IDENTITY_EMAIL_PARAM: None,
            VERIFY_SSL_PARAM: "true",
        }

        result: IntegrationParameters = build_auth_params(
            mock_action,
        )

        mock_action.get_configuration.assert_called_once_with(
            INTEGRATION_IDENTIFIER,
        )
        assert result.service_account_json == "sa-json-value"
        assert result.project_id == "proj-123"
        assert result.workload_identity_email is None
        assert result.verify_ssl is True

    def test_job_extracts_from_parameters(self) -> None:
        """For SiemplifyJob, reads from .parameters dict."""
        mock_job: MagicMock = MagicMock()
        mock_job.__class__.__name__ = "SiemplifyJob"
        mock_job.parameters = {
            SERVICE_ACCOUNT_JSON_PARAM: "job-sa-json",
            PROJECT_ID_PARAM: "job-proj",
            WORKLOAD_IDENTITY_EMAIL_PARAM: "wi@proj.iam",
            VERIFY_SSL_PARAM: "true",
        }

        result: IntegrationParameters = build_auth_params(mock_job)

        assert result.service_account_json == "job-sa-json"
        assert result.project_id == "job-proj"
        assert result.workload_identity_email == "wi@proj.iam"
        assert result.verify_ssl is True

    def test_connector_extracts_from_parameters(self) -> None:
        """For SiemplifyConnectorExecution, reads from .parameters."""
        mock_connector: MagicMock = MagicMock()
        mock_connector.__class__.__name__ = "SiemplifyConnectorExecution"
        mock_connector.parameters = {
            SERVICE_ACCOUNT_JSON_PARAM: "conn-sa",
            PROJECT_ID_PARAM: "conn-proj",
            WORKLOAD_IDENTITY_EMAIL_PARAM: None,
            VERIFY_SSL_PARAM: "false",
        }

        result: IntegrationParameters = build_auth_params(
            mock_connector,
        )

        assert result.service_account_json == "conn-sa"
        assert result.project_id == "conn-proj"
        assert result.verify_ssl is False

    def test_unsupported_type_raises(self) -> None:
        """Raises GoogleSecretManagerError for unknown SDK types."""
        mock_unknown: MagicMock = MagicMock()
        mock_unknown.__class__.__name__ = "UnknownSDKClass"

        with pytest.raises(
            GoogleSecretManagerError,
            match="not supported",
        ):
            build_auth_params(mock_unknown)

    def test_returns_named_tuple(self) -> None:
        """Result is an IntegrationParameters NamedTuple."""
        mock_job: MagicMock = MagicMock()
        mock_job.__class__.__name__ = "SiemplifyJob"
        mock_job.parameters = {
            SERVICE_ACCOUNT_JSON_PARAM: "x",
            PROJECT_ID_PARAM: "y",
            WORKLOAD_IDENTITY_EMAIL_PARAM: "z",
            VERIFY_SSL_PARAM: "true",
        }

        result = build_auth_params(mock_job)

        assert isinstance(result, IntegrationParameters)
        assert result == IntegrationParameters(
            service_account_json="x",
            project_id="y",
            workload_identity_email="z",
            verify_ssl=True,
        )

    def test_verify_ssl_defaults_to_true(self) -> None:
        """verify_ssl defaults to True when the parameter is absent."""
        mock_job: MagicMock = MagicMock()
        mock_job.__class__.__name__ = "SiemplifyJob"
        mock_job.parameters = {
            SERVICE_ACCOUNT_JSON_PARAM: "x",
            PROJECT_ID_PARAM: "y",
            WORKLOAD_IDENTITY_EMAIL_PARAM: None,
            # VERIFY_SSL_PARAM intentionally omitted
        }

        result = build_auth_params(mock_job)

        assert result.verify_ssl is True

    def test_verify_ssl_false_extracted_correctly(self) -> None:
        """verify_ssl is False when the checkbox sends the string 'false'."""
        mock_job: MagicMock = MagicMock()
        mock_job.__class__.__name__ = "SiemplifyJob"
        mock_job.parameters = {
            SERVICE_ACCOUNT_JSON_PARAM: "x",
            PROJECT_ID_PARAM: "y",
            WORKLOAD_IDENTITY_EMAIL_PARAM: None,
            VERIFY_SSL_PARAM: "false",
        }

        result = build_auth_params(mock_job)

        assert result.verify_ssl is False


class TestGetCredentialsFunctions:
    """Tests for credentials helper functions."""

    def test_get_credentials_using_service_account_success(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Resolves credentials and project_id from SA json."""
        sa_json = make_sa_json(project_id="test-proj")
        creds, resolved_proj = _get_credentials_using_service_account(sa_json)
        assert creds is mock_sa_credentials
        assert resolved_proj == "test-proj"

    def test_get_credentials_using_service_account_override_project_id(
        self,
        mock_sa_credentials: MagicMock,
    ) -> None:
        """Resolves credentials and prefers explicit project ID over JSON."""
        sa_json = make_sa_json(project_id="json-proj")
        creds, resolved_proj = _get_credentials_using_service_account(sa_json, project_id="explicit-proj")
        assert creds is mock_sa_credentials
        assert resolved_proj == "explicit-proj"

    def test_get_credentials_using_service_account_invalid_json_raises(self) -> None:
        """Raises InvalidConfigurationError if SA JSON is invalid."""
        with pytest.raises(InvalidConfigurationError, match="Invalid Service Account"):
            _get_credentials_using_service_account("invalid-json{")

    def test_get_credentials_using_workload_identity_email_success(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Builds impersonated credentials."""
        mock_source_creds = MagicMock()
        monkeypatch.setattr(
            "google.auth.default",
            lambda scopes: (mock_source_creds, None),
        )
        mock_impersonated = MagicMock()
        monkeypatch.setattr(
            "google.auth.impersonated_credentials.Credentials",
            lambda **kwargs: mock_impersonated,
        )

        creds = _get_credentials_using_workload_identity_email("sa@proj.iam.gserviceaccount.com")
        assert creds is mock_impersonated

    def test_get_credentials_using_workload_identity_email_default_creds_failure(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Raises InvalidConfigurationError if application default credentials are not found."""

        def mock_default_raise(scopes: list[str]) -> None:
            msg = "Not found"
            raise google.auth.exceptions.DefaultCredentialsError(msg)

        monkeypatch.setattr("google.auth.default", mock_default_raise)

        with pytest.raises(
            InvalidConfigurationError,
            match="Could not resolve Application Default Credentials",
        ):
            _get_credentials_using_workload_identity_email("sa@proj.iam.gserviceaccount.com")

    def test_get_credentials_workload_identity_preferred(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """get_credentials prefers workload identity if both are provided."""
        mock_impersonated = MagicMock()
        monkeypatch.setattr(
            "google_secret_manager.core.authentication._get_credentials_using_workload_identity_email",
            lambda email: mock_impersonated,
        )

        creds, proj = get_credentials(
            service_account_json="sa-json",
            project_id="test-proj",
            workload_identity_email="sa@proj.iam.gserviceaccount.com",
        )
        assert creds is mock_impersonated
        assert proj == "test-proj"

    def test_get_credentials_no_auth_raises(self) -> None:
        """Raises InvalidConfigurationError if no credentials arguments are provided."""
        with pytest.raises(
            InvalidConfigurationError,
            match="Either 'Service Account JSON' or 'Workload Identity Email' must be provided",
        ):
            get_credentials()


class TestSessionCreation:
    """Tests for prepare_auth_request and create_authorized_session."""

    def test_prepare_auth_request_verify_ssl_true(self) -> None:
        """prepare_auth_request has verify=True by default."""
        req = prepare_auth_request()
        assert req.session.verify is True

    def test_prepare_auth_request_verify_ssl_false(self) -> None:
        """prepare_auth_request sets verify=False when verify_ssl=False."""
        req = prepare_auth_request(verify_ssl=False)
        assert req.session.verify is False

    def test_create_authorized_session_verify_ssl_true(self) -> None:
        """create_authorized_session sets verify=True by default."""
        mock_creds = MagicMock()
        with patch("google_secret_manager.core.authentication.prepare_auth_request") as mock_prepare:
            session = create_authorized_session(mock_creds)
            assert session.verify is True
            mock_prepare.assert_called_once_with(verify_ssl=True)

    def test_create_authorized_session_verify_ssl_false(self) -> None:
        """create_authorized_session sets verify=False when verify_ssl=False."""
        mock_creds = MagicMock()
        with patch("google_secret_manager.core.authentication.prepare_auth_request") as mock_prepare:
            session = create_authorized_session(mock_creds, verify_ssl=False)
            assert session.verify is False
            mock_prepare.assert_called_once_with(verify_ssl=False)
