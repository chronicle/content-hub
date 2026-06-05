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

"""Tests for build_auth_params."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from google_secret_manager.core.auth import (
    IntegrationParameters,
    build_auth_params,
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
            VERIFY_SSL_PARAM: True,
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
            VERIFY_SSL_PARAM: True,
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
            VERIFY_SSL_PARAM: False,
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
            VERIFY_SSL_PARAM: True,
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
        """verify_ssl is False when the checkbox parameter is disabled."""
        mock_job: MagicMock = MagicMock()
        mock_job.__class__.__name__ = "SiemplifyJob"
        mock_job.parameters = {
            SERVICE_ACCOUNT_JSON_PARAM: "x",
            PROJECT_ID_PARAM: "y",
            WORKLOAD_IDENTITY_EMAIL_PARAM: None,
            VERIFY_SSL_PARAM: False,
        }

        result = build_auth_params(mock_job)

        assert result.verify_ssl is False
