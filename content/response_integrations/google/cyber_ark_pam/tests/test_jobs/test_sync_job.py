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

"""Tests for CyberArk PAM SyncIntegrationCredentialJob internal methods."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from cyber_ark_pam.jobs.sync_integration_credential_job import (
    SyncIntegrationCredentialJob,
)
from cyber_ark_pam.core.exceptions import (
    IntegrationCredentialSyncError,
    InvalidConfigurationError,
)


class MockParams:
    def __init__(self):
        self.environment_name = "Default Environment"
        self.credential_mapping = "{}"
        self.api_root = "https://mock-pam"
        self.username = "user"
        self.password = "pass"
        self.verify_ssl = False
        self.ca_certificate = None
        self.client_certificate = None
        self.client_certificate_passphrase = None
        self.reason = "Credential Synchronization Job"
        self.ticketing_system_name = None
        self.ticket_id = None


def _make_job() -> SyncIntegrationCredentialJob:
    """Create a job instance with mocked SOAR internals."""
    job = SyncIntegrationCredentialJob.__new__(
        SyncIntegrationCredentialJob,
    )
    job.cyber_ark_manager = None
    job.credential_mapping = {}
    job.instance_name_to_identifier = {}
    job.connector_name_to_identifier = {}
    job.name_id = "SyncIntegrationCredentialJob"
    job.state_context = {}
    job._secret_cache = {}
    job.job_start_time = int(time.time() * 1000)
    type(job).logger = PropertyMock(return_value=MagicMock())

    # Use MockParams with attribute-style access.
    type(job).params = PropertyMock(return_value=MockParams())

    return job


# -------------------------------------------------------------------
# Credential Mapping Parsing
# -------------------------------------------------------------------


class TestValidateParams:
    """Tests for _validate_params."""

    def test_valid_json(self) -> None:
        """Parses valid JSON credential mapping with valid resource names."""
        job = _make_job()
        job.params.credential_mapping = '{"integration_instances": {"inst1": {"p1": "accounts/123_45"}}}'

        job._validate_params()

        assert "integration_instances" in job.credential_mapping
        assert job.credential_mapping["integration_instances"] == {
            "inst1": {"p1": "accounts/123_45"},
        }

    def test_valid_yaml(self) -> None:
        """Parses valid YAML credential mapping with valid resource names."""
        job = _make_job()
        job.params.credential_mapping = (
            "integration_instances:\n  inst1:\n    p1: accounts/123_45/versions/3\n"
        )

        job._validate_params()

        assert "integration_instances" in job.credential_mapping

    def test_empty_mapping(self) -> None:
        """Empty string results in empty dict."""
        job = _make_job()
        job.params.credential_mapping = ""

        job._validate_params()

        assert job.credential_mapping == {}

    def test_invalid_yaml_raises(self) -> None:
        """Raises InvalidConfigurationError on bad YAML."""
        job = _make_job()
        job.params.credential_mapping = "{{invalid: yaml: ["

        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid Credential Mapping",
        ):
            job._validate_params()

    def test_invalid_root_key_raises(self) -> None:
        """Raises InvalidConfigurationError on invalid root key."""
        job = _make_job()
        job.params.credential_mapping = '{"invalid_root": {"inst1": {}}}'

        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid root keys",
        ):
            job._validate_params()

    def test_invalid_value_format_raises(self) -> None:
        """Raises InvalidConfigurationError on invalid parameter value format."""
        job = _make_job()
        job.params.credential_mapping = '{"integration_instances": {"inst1": {"p1": "short-secret-name"}}}'

        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid format for parameter",
        ):
            job._validate_params()


# -------------------------------------------------------------------
# Account + Version Resolution
# -------------------------------------------------------------------


class TestResolveAccountAndVersion:
    """Tests for _resolve_account_and_version."""

    @pytest.mark.anyio
    async def test_explicit_version(self) -> None:
        """'accounts/123_45/versions/3' returns ('123_45', 3)."""
        job = _make_job()

        account_id, version_id = await job._resolve_account_and_version(
            "accounts/123_45/versions/3",
        )

        assert account_id == "123_45"
        assert version_id == 3

    @pytest.mark.anyio
    async def test_no_version(self) -> None:
        """'accounts/123_45' returns ('123_45', None)."""
        job = _make_job()

        account_id, version_id = await job._resolve_account_and_version(
            "accounts/123_45",
        )

        assert account_id == "123_45"
        assert version_id is None

    @pytest.mark.anyio
    async def test_invalid_format_raises(self) -> None:
        """Raises InvalidConfigurationError on invalid format."""
        job = _make_job()

        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid credential mapping format",
        ):
            await job._resolve_account_and_version("invalid/path")


# -------------------------------------------------------------------
# Sync Execution Flow
# -------------------------------------------------------------------


class TestSyncFlow:
    """Tests for overall sync flow internal parts."""

    @pytest.mark.anyio
    async def test_sync_integration_instances_success(self) -> None:
        """Tests successful synchronization of integration instances."""
        job = _make_job()
        job.credential_mapping = {
            "integration_instances": {
                "Akeyless": {
                    "Password": "accounts/123_45"
                }
            }
        }
        
        mock_api = AsyncMock()
        mock_api.get_installed_integrations_of_environment.return_value = {
            "instances": [
                {"displayName": "Akeyless", "identifier": "Akeyless_Instance_1"}
            ]
        }

        mock_manager = MagicMock()
        mock_manager.get_password.return_value = '"secret_password"'
        job.cyber_ark_manager = mock_manager

        semaphore = asyncio.Semaphore(1)
        await job._sync_integration_instances(mock_api, semaphore)

        # Should invoke get_password and set_configuration_property
        mock_manager.get_password.assert_called_once_with(
            account="123_45",
            reason="Credential Synchronization Job",
            ticketing_system_name=None,
            ticket_id=None,
            version=None,
        )
        mock_api.set_configuration_property.assert_called_once_with(
            integration_instance_identifier="Akeyless_Instance_1",
            property_name="Password",
            property_value="secret_password",
        )

    @pytest.mark.anyio
    async def test_sync_connectors_success(self) -> None:
        """Tests successful synchronization of connectors."""
        job = _make_job()
        job.credential_mapping = {
            "connectors": {
                "Akeyless Connector": {
                    "Token": "accounts/123_45/versions/5"
                }
            }
        }

        mock_api = AsyncMock()
        mock_api.get_connector_cards.return_value = {
            "connectorInstances": [
                {"displayName": "Akeyless Connector", "identifier": "Conn_1"}
            ]
        }

        mock_manager = MagicMock()
        mock_manager.get_password.return_value = "token_value"
        job.cyber_ark_manager = mock_manager

        semaphore = asyncio.Semaphore(1)
        await job._sync_connectors(mock_api, semaphore)

        mock_manager.get_password.assert_called_once_with(
            account="123_45",
            reason="Credential Synchronization Job",
            ticketing_system_name=None,
            ticket_id=None,
            version=5,
        )
        mock_api.set_connector_parameter.assert_called_once_with(
            connector_instance_identifier="Conn_1",
            parameter_name="Token",
            parameter_value="token_value",
        )

    @pytest.mark.anyio
    async def test_sync_jobs_success(self) -> None:
        """Tests successful synchronization of jobs."""
        job = _make_job()
        job.credential_mapping = {
            "jobs": {
                "Sync Job": {
                    "API Key": "accounts/999_88"
                }
            }
        }

        mock_api = AsyncMock()
        mock_api.get_installed_jobs.side_effect = [
            [{"name": "Sync Job", "id": "Job_1", "parameters": [{"displayName": "API Key", "value": "old"}]}]
        ]

        mock_manager = MagicMock()
        mock_manager.get_password.return_value = "new_api_key"
        job.cyber_ark_manager = mock_manager

        semaphore = asyncio.Semaphore(1)
        await job._sync_jobs(mock_api, semaphore)

        mock_manager.get_password.assert_called_once_with(
            account="999_88",
            reason="Credential Synchronization Job",
            ticketing_system_name=None,
            ticket_id=None,
            version=None,
        )
        mock_api.save_or_update_job.assert_called_once()
        saved_job_data = mock_api.save_or_update_job.call_args[1]["job_data"]
        assert saved_job_data["parameters"][0]["value"] == "new_api_key"
