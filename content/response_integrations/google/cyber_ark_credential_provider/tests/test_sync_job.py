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

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest
from cyber_ark_credential_provider.core.constants import (
    CONNECTORS_KEY,
    INTEGRATION_INSTANCES_KEY,
    JOBS_KEY,
    SUCCESS_EXIT_CODE,
)
from cyber_ark_credential_provider.core.credential_provider_manager import CommandResult
from cyber_ark_credential_provider.jobs.sync_integration_credentials_job import (
    SyncIntegrationCredentialJob,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _make_job() -> SyncIntegrationCredentialJob:
    """Create a job instance with mocked SOAR internals."""
    job = SyncIntegrationCredentialJob.__new__(SyncIntegrationCredentialJob)
    job._api_client = MagicMock()
    job.credential_mapping = {}
    job.environment_name = "Default Environment"
    job.instance_name_to_identifier = {}
    job.connector_name_to_identifier = {}
    job.name_id = "SyncIntegrationCredentialJob"
    job._secret_cache = {}
    job.execution_errors = []
    job.configuration_parameters = None
    job.job_start_time = int(time.time() * 1000)
    type(job).logger = PropertyMock(return_value=MagicMock())

    # Mock self.params with attribute-style access.
    mock_params = MagicMock()
    mock_params.environment_name = "Default Environment"
    mock_params.credential_mapping = "{}"
    mock_params.docker_gateway_ip = "172.17.0.1"
    mock_params.docker_gateway_ip_address = "172.17.0.1"
    mock_params.path_to_clipasswordsdk = "/opt/CARKaim/sdk/clipasswordsdk"
    mock_params.pathtoclipasswordsdk = "/opt/CARKaim/sdk/clipasswordsdk"
    mock_params.username_for_credential_provider_for_linux = "secopsuser"
    mock_params.usernamefor_credential_providerfor_linux = "secopsuser"
    mock_params.host_public_key = "dGVzdF9rZXk="
    mock_params.ssh_private_key_path = "/path/to/key"
    mock_params.password_for_credential_provider_for_linux = "secret_pass"
    mock_params.passwordfor_credential_providerfor_linux = "secret_pass"
    type(job).params = PropertyMock(return_value=mock_params)

    # Mock soar_job
    mock_soar_job = MagicMock()
    type(job).soar_job = PropertyMock(return_value=mock_soar_job)

    return job


# -------------------------------------------------------------------
# Parameter Validation
# -------------------------------------------------------------------


class TestValidateParams:
    """Tests for _validate_params."""

    def test_valid_json(self, mocker) -> None:
        """Parses valid JSON credential mapping."""
        job = _make_job()
        job.params.credential_mapping = '{"integration_instances": {"inst1": {}}}'
        mocker.patch.object(
            job,
            "_get_configuration_parameters",
            return_value=MagicMock(docker_gateway_ip="127.0.0.1"),
        )
        mocker.patch(
            "cyber_ark_credential_provider.jobs.sync_integration_credentials_job.validate_ip_address"
        )

        job._validate_params()

        assert INTEGRATION_INSTANCES_KEY in job.credential_mapping
        assert job.credential_mapping[INTEGRATION_INSTANCES_KEY] == {"inst1": {}}

    def test_empty_mapping(self, mocker) -> None:
        """Empty string results in empty dict."""
        job = _make_job()
        job.params.credential_mapping = ""
        mocker.patch.object(
            job,
            "_get_configuration_parameters",
            return_value=MagicMock(docker_gateway_ip="127.0.0.1"),
        )
        mocker.patch(
            "cyber_ark_credential_provider.jobs.sync_integration_credentials_job.validate_ip_address"
        )

        job._validate_params()

        assert job.credential_mapping == {}

    def test_invalid_json_raises(self) -> None:
        """Raises ValueError on bad JSON."""
        job = _make_job()
        job.params.credential_mapping = "{{invalid: json: ["

        with pytest.raises(
            ValueError,
            match="Invalid Credential Mapping JSON",
        ):
            job._validate_params()


# -------------------------------------------------------------------
# Secret Fetch Caching
# -------------------------------------------------------------------


class TestSecretFetchCaching:
    """Tests for dictionary-based caching of secret fetches."""

    @pytest.mark.anyio
    async def test_caches_subsequent_fetches(self) -> None:
        """Only fetches once and uses cached payload for subsequent requests."""
        job = _make_job()
        mock_result = CommandResult(
            output="secret-payload\n", error="", exit_code=SUCCESS_EXIT_CODE
        )
        job.api_client.get_password_from_location.return_value = mock_result

        # First call
        val1 = await job._get_secret_from_cyberark_async("safe=A;object=B")
        # Second call
        val2 = await job._get_secret_from_cyberark_async("safe=A;object=B")

        assert val1 == "secret-payload"
        assert val2 == "secret-payload"

        # The client should have been called exactly once
        job.api_client.get_password_from_location.assert_called_once_with(
            secret_location="safe=A;object=B"
        )
        assert job._secret_cache["safe=A;object=B"] == "secret-payload"


# -------------------------------------------------------------------
# Concurrency & Sync Logic
# -------------------------------------------------------------------


class TestSyncExecution:
    """Tests for concurrent update execution methods."""

    @pytest.mark.anyio
    async def test_sync_integration_instances_updates(self) -> None:
        """Updates integration instance parameters on every sync run."""
        job = _make_job()
        job.credential_mapping = {
            INTEGRATION_INSTANCES_KEY: {"Instance A": {"param_x": "secret_id"}}
        }
        job.instance_name_to_identifier = {"Instance A": "inst_id"}

        job._get_secret_from_cyberark_async = AsyncMock(return_value="new-value")

        mock_api = AsyncMock()
        mock_api.get_installed_integrations_of_environment.return_value = [
            {
                "instanceName": "Instance A",
                "identifier": "inst_id",
                "integrationIdentifier": "CyberArkCredentialProvider",
            }
        ]
        semaphore = asyncio.Semaphore(10)

        await job._sync_integration_instances(mock_api, semaphore)

        mock_api.set_configuration_property.assert_called_once_with(
            integration_instance_identifier="inst_id",
            property_name="param_x",
            property_value="new-value",
        )

    @pytest.mark.anyio
    async def test_sync_connectors_updates(self) -> None:
        """Updates connector parameters on every sync run."""
        job = _make_job()
        job.credential_mapping = {
            CONNECTORS_KEY: {"Connector A": {"param_y": "secret_id"}}
        }
        job.connector_name_to_identifier = {"Connector A": "conn_id"}

        job._get_secret_from_cyberark_async = AsyncMock(return_value="new-value")

        mock_api = AsyncMock()
        mock_api.get_connector_cards.return_value = {
            "connectorInstances": [
                {
                    "displayName": "Connector A",
                    "identifier": "conn_id",
                    "integration": "CyberArkCredentialProvider",
                }
            ]
        }
        semaphore = asyncio.Semaphore(10)

        await job._sync_connectors(mock_api, semaphore)

        mock_api.set_connector_parameter.assert_called_once_with(
            connector_instance_identifier="conn_id",
            parameter_name="param_y",
            parameter_value="new-value",
        )

    @pytest.mark.anyio
    async def test_sync_jobs_updates_when_outdated(self) -> None:
        """Updates job parameters from CyberArk secret."""
        job = _make_job()
        job.credential_mapping = {JOBS_KEY: {"Job A": {"param_z": "secret_id"}}}

        job_instances = [
            {
                "displayName": "Job A",
                "id": 100,
                "parameters": [{"displayName": "param_z", "value": "old"}],
            }
        ]
        job._fetch_job_instances = AsyncMock(return_value=job_instances)
        job._get_secret_from_cyberark_async = AsyncMock(return_value="new-value")

        mock_api = AsyncMock()
        semaphore = asyncio.Semaphore(10)

        await job._sync_jobs(mock_api, semaphore)

        mock_api.save_or_update_job.assert_called_once()

    @pytest.mark.anyio
    async def test_prefetch_all_secrets_deduplicates_and_caches(self) -> None:
        """Pre-fetches unique secret locations concurrently into cache."""
        job = _make_job()
        job.credential_mapping = {
            INTEGRATION_INSTANCES_KEY: {
                "Instance A": {"param_x": "secret_1"},
                "Instance B": {"param_y": "secret_1"},
            },
            CONNECTORS_KEY: {"Connector A": {"param_z": "secret_2"}},
        }
        mock_result = CommandResult(output="val_secret", error="", exit_code=0)
        job.api_client.get_password_from_location = MagicMock(return_value=mock_result)

        semaphore = asyncio.Semaphore(10)
        await job._prefetch_all_secrets(semaphore)

        assert job.api_client.get_password_from_location.call_count == 2
        assert job._secret_cache["secret_1"] == "val_secret"
        assert job._secret_cache["secret_2"] == "val_secret"


class TestGetConfigurationParameters:
    """Tests for _get_configuration_parameters."""

    def test_fallback_attribute_names(self) -> None:
        """Correctly extracts configuration parameters when camel_to_snake_case produces names without underscores."""
        job = SyncIntegrationCredentialJob.__new__(SyncIntegrationCredentialJob)
        job.configuration_parameters = None

        mock_params = MagicMock(spec=[])
        mock_params.pathtoclipasswordsdk = "/opt/CARKaim/sdk/clipasswordsdk"
        mock_params.usernamefor_credential_providerfor_linux = "secopsuser"
        mock_params.passwordfor_credential_providerfor_linux = "secret_pass"
        mock_params.docker_gateway_ip_address = "172.17.0.1"
        mock_params.host_public_key = "dGVzdF_rZXk="
        mock_params.ssh_private_key_path = None

        type(job).params = PropertyMock(return_value=mock_params)

        config_params = job._get_configuration_parameters()

        assert str(config_params.sdk_path) == "/opt/CARKaim/sdk/clipasswordsdk"
        assert config_params.username == "secopsuser"
        assert config_params.password == "secret_pass"
        assert config_params.docker_gateway_ip == "172.17.0.1"


# -------------------------------------------------------------------
# Invalid Environment & Error Propagation Tests
# -------------------------------------------------------------------


class TestInvalidEnvironmentHandling:
    """Tests for invalid environment name handling and error propagation."""

    @pytest.mark.anyio
    async def test_empty_instances_records_error_and_skips_loop(self) -> None:
        """When instances_list is empty, records error and returns None without looping."""
        job = _make_job()
        job.environment_name = "InvalidEnv"
        job.credential_mapping = {
            INTEGRATION_INSTANCES_KEY: {
                "Instance A": {"param_x": "secret_1"},
                "Instance B": {"param_y": "secret_2"},
            }
        }

        mock_api = AsyncMock()
        mock_api.get_installed_integrations_of_environment.return_value = []
        semaphore = asyncio.Semaphore(10)

        result = await job._sync_integration_instances(mock_api, semaphore)

        assert result is None
        assert len(job.execution_errors) == 1
        assert (
            "Either the environment name 'InvalidEnv' is invalid or no integration instances are configured in that environment."
            in job.execution_errors[0]
        )
        assert mock_api.set_configuration_property.call_count == 0

    @pytest.mark.anyio
    async def test_async_main_fails_job_when_execution_errors_present(
        self, mocker
    ) -> None:
        """_async_main raises CyberArkCredentialProviderSyncError if errors occurred."""
        from cyber_ark_credential_provider.core.exceptions import CyberArkCredentialProviderSyncError

        job = _make_job()
        job.params.environment_name = "NonExistentEnv"
        job.credential_mapping = {
            INTEGRATION_INSTANCES_KEY: {"Instance A": {"param_x": "secret_1"}}
        }

        mock_api = AsyncMock()
        mock_api.get_installed_integrations_of_environment.return_value = []
        job._prefetch_all_secrets = AsyncMock()

        mocker.patch(
            "cyber_ark_credential_provider.jobs.sync_integration_credentials_job.AsyncChronicleSOAR",
            return_value=AsyncMock(),
        )
        mocker.patch(
            "cyber_ark_credential_provider.jobs.sync_integration_credentials_job.AsyncMarketplaceApi",
            return_value=mock_api,
        )

        with pytest.raises(
            CyberArkCredentialProviderSyncError,
            match="Sync completed with errors",
        ):
            await job._async_main()

