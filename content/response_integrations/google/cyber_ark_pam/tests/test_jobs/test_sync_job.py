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

from cyber_ark_pam.core.exceptions import (
    IntegrationCredentialSyncError,
    InvalidConfigurationError,
    JobSaveError,
)
from cyber_ark_pam.jobs.sync_integration_credential_job import (
    SyncIntegrationCredentialJob,
)


class MockParams:
    def __init__(self) -> None:
        self.environment_name = "Default Environment"
        self.credential_mapping = "{}"
        self.api_root = "https://mock-pam"
        self.username = "user"
        self.password = "pass"  # noqa: S105
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

    def test_explicit_version(self) -> None:
        """'accounts/123_45/versions/3' returns ('123_45', 3)."""
        job = _make_job()

        account_id, version_id = job._resolve_account_and_version(
            "accounts/123_45/versions/3",
        )

        assert account_id == "123_45"
        assert version_id == 3

    def test_no_version(self) -> None:
        """'accounts/123_45' returns ('123_45', None)."""
        job = _make_job()

        account_id, version_id = job._resolve_account_and_version(
            "accounts/123_45",
        )

        assert account_id == "123_45"
        assert version_id is None

    def test_invalid_format_raises(self) -> None:
        """Raises InvalidConfigurationError on invalid format."""
        job = _make_job()

        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid credential mapping format",
        ):
            job._resolve_account_and_version("invalid/path")


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


# -------------------------------------------------------------------
# State Context Registry & Skipping Logic
# -------------------------------------------------------------------


class TestStateContextRegistry:
    """Tests for persistent state context registry and skipping logic."""

    def test_load_context_success(self) -> None:
        """Loads valid JSON context state from soar_job."""
        job = _make_job()
        mock_soar_job = MagicMock()
        mock_soar_job.get_job_context_property.return_value = '{"instance:id1:p1": "accounts/123::10"}'
        type(job).soar_job = PropertyMock(return_value=mock_soar_job)

        job._load_context()

        assert job.state_context == {"instance:id1:p1": "accounts/123::10"}

    def test_load_context_empty(self) -> None:
        """Handles empty context state string gracefully."""
        job = _make_job()
        mock_soar_job = MagicMock()
        mock_soar_job.get_job_context_property.return_value = ""
        type(job).soar_job = PropertyMock(return_value=mock_soar_job)

        job._load_context()

        assert job.state_context == {}

    def test_load_context_invalid_json(self) -> None:
        """Handles invalid JSON string gracefully."""
        job = _make_job()
        mock_soar_job = MagicMock()
        mock_soar_job.get_job_context_property.return_value = "invalid-json-{"
        type(job).soar_job = PropertyMock(return_value=mock_soar_job)

        job._load_context()

        assert job.state_context == {}

    def test_save_context_success(self) -> None:
        """Saves state_context as JSON string successfully."""
        job = _make_job()
        mock_soar_job = MagicMock()
        type(job).soar_job = PropertyMock(return_value=mock_soar_job)
        job.state_context = {"instance:id1:p1": "accounts/123::10"}

        job._save_context()

        mock_soar_job.set_job_context_property.assert_called_once_with(
            identifier=job.name_id,
            property_key="sync_credentials_state",
            property_value='{"instance:id1:p1": "accounts/123::10"}',
        )


class TestSkippingLogic:
    """Tests for conditional parameter updating and skipping logic."""

    @pytest.mark.anyio
    async def test_set_integration_params_skips_when_up_to_date(self) -> None:
        """Skips fetching and setting configuration when parameter is up-to-date."""
        job = _make_job()
        job.state_context = {"instance:inst_id:param_x": "accounts/123::None"}

        job._fetch_secret_value_pre_resolved = AsyncMock()
        mock_api = AsyncMock()

        await job._set_integration_params(
            api=mock_api,
            name="Instance A",
            identifier="inst_id",
            param_mapping={"param_x": "accounts/123"},
        )

        job._fetch_secret_value_pre_resolved.assert_not_called()
        mock_api.set_configuration_property.assert_not_called()

    @pytest.mark.anyio
    async def test_set_integration_params_updates_when_outdated(self) -> None:
        """Updates and saves to context when parameter is outdated or not present."""
        job = _make_job()
        job.state_context = {}

        job._fetch_secret_value_pre_resolved = AsyncMock(return_value="secret-pass")
        mock_api = AsyncMock()

        await job._set_integration_params(
            api=mock_api,
            name="Instance A",
            identifier="inst_id",
            param_mapping={"param_x": "accounts/123/versions/2"},
        )

        job._fetch_secret_value_pre_resolved.assert_called_once_with(
            "123",
            2,
            context_label="param 'param_x' on instance 'Instance A' (id: inst_id)",
        )
        mock_api.set_configuration_property.assert_called_once_with(
            integration_instance_identifier="inst_id",
            property_name="param_x",
            property_value="secret-pass",
        )
        assert job.state_context["instance:inst_id:param_x"] == "accounts/123/versions/2::2"

    @pytest.mark.anyio
    async def test_update_single_job_state_updates_on_success(self) -> None:
        """State is updated when job update successfully persists."""
        job = _make_job()
        job.state_context = {}
        mock_api = AsyncMock()
        job._fetch_secret_value_pre_resolved = AsyncMock(return_value="new-secret")

        param_mapping = {"API Key": "accounts/999_88"}
        parameters = [{"displayName": "API Key", "value": "old"}]
        name_to_job = {
            "Sync Job": {
                "name": "Sync Job",
                "id": "Job_1",
                "parameters": parameters,
            }
        }

        await job._update_single_job(
            api=mock_api,
            job_name="Sync Job",
            param_mapping=param_mapping,
            name_to_job=name_to_job,
        )

        mock_api.save_or_update_job.assert_called_once()
        assert job.state_context["job:Sync Job:API Key"] == "accounts/999_88::None"

    @pytest.mark.anyio
    async def test_update_single_job_state_not_updated_on_failure(self) -> None:
        """State is not updated if saving the job fails."""
        job = _make_job()
        job.state_context = {}
        mock_api = AsyncMock()
        mock_api.save_or_update_job.side_effect = JobSaveError("Failed to save")
        job._fetch_secret_value_pre_resolved = AsyncMock(return_value="new-secret")

        param_mapping = {"API Key": "accounts/999_88"}
        parameters = [{"displayName": "API Key", "value": "old"}]
        name_to_job = {
            "Sync Job": {
                "name": "Sync Job",
                "id": "Job_1",
                "parameters": parameters,
            }
        }

        with pytest.raises(JobSaveError):
            await job._update_single_job(
                api=mock_api,
                job_name="Sync Job",
                param_mapping=param_mapping,
                name_to_job=name_to_job,
            )

        assert "job:Sync Job:API Key" not in job.state_context


# -------------------------------------------------------------------
# Secret Fetch Caching & Timeout
# -------------------------------------------------------------------


class TestSecretFetchCaching:
    """Tests for dictionary-based caching of secret fetches."""

    @pytest.mark.anyio
    async def test_caches_subsequent_fetches(self) -> None:
        """Only fetches once and uses cached payload for subsequent requests."""
        job = _make_job()
        mock_manager = MagicMock()
        mock_manager.get_password.return_value = "cached_pwd"
        job.cyber_ark_manager = mock_manager

        # First call
        val1 = await job._fetch_secret_value_pre_resolved(
            account_id="acc-1",
            version_id=None,
            context_label="first call",
        )

        # Second call (same secret and version)
        val2 = await job._fetch_secret_value_pre_resolved(
            account_id="acc-1",
            version_id=None,
            context_label="second call",
        )

        assert val1 == "cached_pwd"
        assert val2 == "cached_pwd"

        # The manager's get_password should have been called exactly once
        mock_manager.get_password.assert_called_once_with(
            account="acc-1",
            reason="Credential Synchronization Job",
            ticketing_system_name=None,
            ticket_id=None,
            version=None,
        )
        assert job._secret_cache["acc-1", None] == "cached_pwd"


class TestTimeoutHandling:
    """Tests for timeout handling."""

    def test_approaching_timeout_false(self) -> None:
        """Returns False if job is not approaching the threshold."""
        job = _make_job()
        job.job_start_time = int(time.time() * 1000)
        assert job._is_approaching_timeout() is False

    def test_approaching_timeout_true(self) -> None:
        """Returns True if execution duration exceeds TIMEOUT_THRESHOLD_MS."""
        job = _make_job()
        # Mock start time as 10 hours ago
        job.job_start_time = int(time.time() * 1000) - (10 * 60 * 60 * 1000)
        assert job._is_approaching_timeout() is True

    @pytest.mark.anyio
    async def test_timeout_raises_if_errors_exist(self) -> None:
        """Raises IntegrationCredentialSyncError on timeout if preceding errors exist."""
        job = _make_job()
        job._soar_job = MagicMock()
        job._sync_errors = ["Some integration sync error"]

        with (
            patch.object(job, "_is_approaching_timeout", return_value=True),
            patch.object(job, "_init_cyber_ark_pam_client"),
            patch.object(job, "_load_context"),
            patch.object(job, "_save_context"),
            patch(
                "cyber_ark_pam.jobs.sync_integration_credential_job.AsyncChronicleSOAR"
            ) as mock_soar_cls,
            patch(
                "cyber_ark_pam.jobs.sync_integration_credential_job.AsyncMarketplaceApi"
            ) as mock_market_cls,
        ):
            mock_soar = AsyncMock()
            mock_soar_cls.return_value = mock_soar
            mock_market = AsyncMock()
            mock_market_cls.return_value = mock_market

            # Mock the sync methods called before timeout checks
            job._sync_integration_instances = AsyncMock()

            with pytest.raises(IntegrationCredentialSyncError):
                await job._async_main()


# -------------------------------------------------------------------
# Error Collection & Sync Job Failure
# -------------------------------------------------------------------


class TestAggregatedErrors:
    """Tests for aggregated error collection and failure at the end of the sync job."""

    @pytest.mark.anyio
    async def test_sync_errors_collected_and_fails_job(self) -> None:
        """Collects errors from various failing components and raises IntegrationCredentialSyncError."""
        job = _make_job()
        job._soar_job = MagicMock()
        job.params.credential_mapping = (
            '{"integration_instances": {"inst1": {}}, "connectors": {"conn1": {}}, "jobs": {"job1": {}}}'
        )
        job._validate_params()
        job._sync_errors = []

        # Mock APIs to simulate components not found
        job.instance_name_to_identifier = {}
        job.connector_name_to_identifier = {}

        mock_api = AsyncMock()
        mock_api.get_installed_integrations_of_environment.return_value = {
            "instances": [{"displayName": "other-inst", "identifier": "other-inst-id"}]
        }
        mock_api.get_connector_cards.return_value = {
            "connectorInstances": [{"displayName": "other-conn", "identifier": "other-conn-id"}]
        }
        mock_api.get_installed_jobs.return_value = [
            {"displayName": "other-job", "id": "other-job-id", "parameters": []}
        ]

        # Call individual sync functions
        await job._sync_integration_instances(mock_api, asyncio.Semaphore(1))
        await job._sync_connectors(mock_api, asyncio.Semaphore(1))
        await job._sync_jobs(mock_api, asyncio.Semaphore(1))

        # Verify errors are collected
        assert len(job._sync_errors) == 3
        assert any("Integration instance 'inst1' not found" in err for err in job._sync_errors)
        assert any("Connector 'conn1' not found" in err for err in job._sync_errors)
        assert any("Job 'job1' not found" in err for err in job._sync_errors)

        # Mock the entire _async_main calling flow with these sync errors
        with (
            patch.object(job, "_init_cyber_ark_pam_client"),
            patch.object(job, "_load_context"),
            patch.object(job, "_save_context"),
            patch(
                "cyber_ark_pam.jobs.sync_integration_credential_job.AsyncChronicleSOAR"
            ) as mock_soar_cls,
            patch(
                "cyber_ark_pam.jobs.sync_integration_credential_job.AsyncMarketplaceApi"
            ) as mock_market_cls,
        ):
            mock_soar = AsyncMock()
            mock_soar_cls.return_value = mock_soar

            # Mock the marketplace API methods
            mock_market = AsyncMock()
            mock_market.get_installed_integrations_of_environment.return_value = {
                "instances": [{"displayName": "other-inst", "identifier": "other-inst-id"}]
            }
            mock_market.get_connector_cards.return_value = {
                "connectorInstances": [{"displayName": "other-conn", "identifier": "other-conn-id"}]
            }
            mock_market.get_installed_jobs.return_value = [
                {"displayName": "other-job", "id": "other-job-id", "parameters": []}
            ]
            mock_market_cls.return_value = mock_market

            # Run _async_main and assert it raises IntegrationCredentialSyncError
            with pytest.raises(IntegrationCredentialSyncError) as exc_info:
                await job._async_main()

            assert "Credential synchronization completed with one or more errors" in str(exc_info.value)
            assert "Integration instance 'inst1' not found" in str(exc_info.value)
            assert "Connector 'conn1' not found" in str(exc_info.value)
            assert "Job 'job1' not found" in str(exc_info.value)
