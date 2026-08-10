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

"""Tests for SyncIntegrationCredentialJob internal methods."""

from __future__ import annotations

# ruff:file-ignore[hardcoded-password-string, hardcoded-password-func-arg]
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from akeyless.core.constants import DEFAULT_SECRET_VERSION
from akeyless.core.exceptions import (
    IntegrationCredentialSyncError,
    InvalidConfigurationError,
)
from akeyless.jobs.sync_integration_credentials_job import (
    SyncIntegrationCredentialsJob,
)


def _make_job() -> SyncIntegrationCredentialsJob:
    """Create a job instance with mocked SOAR internals."""
    job = SyncIntegrationCredentialsJob.__new__(
        SyncIntegrationCredentialsJob,
    )
    job.akeyless_client = None
    job.credential_mapping = {}
    job.environment_name = "Default Environment"
    job.instance_name_to_identifier = {}
    job.connector_name_to_identifier = {}
    job.name_id = "SyncIntegrationCredentialsJob"
    job._secret_cache = {}
    job.execution_errors = []
    job.job_start_time = int(time.time() * 1000)
    type(job).logger = PropertyMock(return_value=MagicMock())

    # Mock self.params with attribute-style access.
    mock_params: MagicMock = MagicMock()
    mock_params.environment_name = "Default Environment"
    mock_params.credential_mapping = "{}"
    type(job).params = PropertyMock(return_value=mock_params)
    type(job).soar_job = PropertyMock(return_value=MagicMock())

    return job


class TestValidateParams:
    """Tests for _validate_params."""

    def test_valid_json(self) -> None:
        """Parses valid JSON credential mapping."""
        job = _make_job()
        job.params.credential_mapping = '{"integration_instances": {"inst1": {}}}'

        job._validate_params()

        assert "integration_instances" in job.credential_mapping
        assert job.credential_mapping["integration_instances"] == {
            "inst1": {},
        }

    def test_empty_mapping(self) -> None:
        """Empty string results in empty dict."""
        job = _make_job()
        job.params.credential_mapping = ""

        job._validate_params()

        assert job.credential_mapping == {}

    def test_invalid_json_raises(self) -> None:
        """Raises InvalidConfigurationError on bad JSON."""
        job = _make_job()
        job.params.credential_mapping = "{invalid json: ["

        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid Credential Mapping JSON syntax",
        ):
            job._validate_params()

    def test_invalid_root_key_raises(self) -> None:
        """Raises InvalidConfigurationError on invalid root keys."""
        job = _make_job()
        job.params.credential_mapping = '{"invalid_key": {}}'

        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid root keys in Credential Mapping",
        ):
            job._validate_params()

    def test_invalid_category_type_raises(self) -> None:
        """Raises InvalidConfigurationError when category is not a dictionary."""
        job = _make_job()
        job.params.credential_mapping = '{"integration_instances": []}'

        with pytest.raises(
            InvalidConfigurationError,
            match="Category 'integration_instances' must be a dictionary",
        ):
            job._validate_params()

    def test_invalid_param_mapping_type_raises(self) -> None:
        """Raises InvalidConfigurationError when param mapping is not a dictionary."""
        job = _make_job()
        job.params.credential_mapping = '{"integration_instances": {"inst1": []}}'

        with pytest.raises(
            InvalidConfigurationError,
            match="Parameters for 'inst1' in category 'integration_instances' must be a dictionary",
        ):
            job._validate_params()

    def test_invalid_mapped_value_format_raises(self) -> None:
        """Raises InvalidConfigurationError on empty/invalid secret formats."""
        job = _make_job()
        job.params.credential_mapping = '{"integration_instances": {"inst1": {"p1": ""}}}'

        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid format for parameter 'p1'",
        ):
            job._validate_params()


class TestResolveSecretAndVersion:
    """Tests for _resolve_secret_and_version."""

    def test_explicit_version(self) -> None:
        """'my-secret:5' returns ('my-secret', '5')."""
        job = _make_job()

        secret_id, version_id = job._resolve_secret_and_version(
            "my-secret:5",
        )

        assert secret_id == "my-secret"
        assert version_id == "5"

    def test_explicit_version_with_colon_in_id(self) -> None:
        """Splits on first colon only: 'a:b:c' -> ('a', 'b:c')."""
        job = _make_job()

        secret_id, version_id = job._resolve_secret_and_version(
            "a:b:c",
        )

        assert secret_id == "a"
        assert version_id == "b:c"

    def test_auto_version_with_client(self) -> None:
        """Calls resolve_latest_enabled_version when no colon."""
        job = _make_job()
        mock_client: MagicMock = MagicMock()
        mock_client.resolve_latest_enabled_version.return_value = "7"
        job.akeyless_client = mock_client

        secret_id, version_id = job._resolve_secret_and_version(
            "my-secret",
        )

        assert secret_id == "my-secret"
        assert version_id == "7"
        mock_client.resolve_latest_enabled_version.assert_called_once_with(
            "my-secret",
        )

    def test_auto_version_no_client_fallback(self) -> None:
        """Falls back to DEFAULT_SECRET_VERSION when client is None."""
        job = _make_job()
        job.akeyless_client = None

        secret_id, version_id = job._resolve_secret_and_version(
            "my-secret",
        )

        assert secret_id == "my-secret"
        assert version_id == DEFAULT_SECRET_VERSION


class TestPrefetchAllSecrets:
    """Tests for _prefetch_all_secrets."""

    @pytest.mark.anyio
    async def test_prefetches_unique_secrets(self) -> None:
        """Prefetches all unique secrets across mapping sections."""
        job = _make_job()
        job.credential_mapping = {
            "integration_instances": {"inst1": {"p1": "secret-a:1", "p2": "secret-b:2"}},
            "connectors": {"conn1": {"p1": "secret-a:1"}},
            "jobs": {"job1": {"p1": "secret-c:3"}},
        }
        mock_client = MagicMock()
        mock_client.get_secret_value.side_effect = lambda secret_id, version_id: f"val-{secret_id}-{version_id}"
        job.akeyless_client = mock_client

        semaphore = asyncio.Semaphore(5)
        await job._prefetch_all_secrets(semaphore)

        assert job._secret_cache["secret-a", "1"] == "val-secret-a-1"
        assert job._secret_cache["secret-b", "2"] == "val-secret-b-2"
        assert job._secret_cache["secret-c", "3"] == "val-secret-c-3"
        assert mock_client.get_secret_value.call_count == 3


class TestSyncIntegrationInstances:
    """Tests for _sync_integration_instances."""

    @pytest.mark.anyio
    async def test_skips_when_empty_mapping(self) -> None:
        """Logs skipping and returns when integration_instances is empty."""
        job = _make_job()
        job.credential_mapping = {}
        mock_api = AsyncMock()
        semaphore = asyncio.Semaphore(5)

        await job._sync_integration_instances(mock_api, semaphore)

        mock_api.get_installed_integrations_of_environment.assert_not_called()
        job.logger.info.assert_called_with("No integration instances in credential mapping. Skipping.")

    @pytest.mark.anyio
    async def test_empty_instances_in_environment_records_error(self) -> None:
        """Records error and returns without processing instances when instances_list is empty."""
        job = _make_job()
        job.credential_mapping = {"integration_instances": {"inst1": {"p1": "sec1"}}}
        job.environment_name = "NonExistentEnv"

        mock_api = AsyncMock()
        mock_api.get_installed_integrations_of_environment.return_value = {"instances": []}
        semaphore = asyncio.Semaphore(5)

        await job._sync_integration_instances(mock_api, semaphore)

        assert len(job.execution_errors) == 1
        assert "Either the environment name 'NonExistentEnv' is invalid" in job.execution_errors[0]
        job.logger.error.assert_called_with(
            "Either the environment name 'NonExistentEnv' is invalid or no "
            "integration instances are configured in that environment."
        )

    @pytest.mark.anyio
    async def test_syncs_instances_success(self) -> None:
        """Successfully syncs instance parameters."""
        job = _make_job()
        job.credential_mapping = {"integration_instances": {"inst1": {"p1": "sec1:1"}}}
        job.environment_name = "Default Environment"
        job._secret_cache["sec1", "1"] = "secret-val-1"

        mock_api = AsyncMock()
        mock_api.get_installed_integrations_of_environment.return_value = {
            "instances": [{"displayName": "inst1", "identifier": "inst1-id"}]
        }
        semaphore = asyncio.Semaphore(5)

        await job._sync_integration_instances(mock_api, semaphore)

        mock_api.set_configuration_property.assert_called_once_with(
            integration_instance_identifier="inst1-id",
            property_name="p1",
            property_value="secret-val-1",
        )
        assert len(job.execution_errors) == 0


class TestSyncConnectors:
    """Tests for _sync_connectors."""

    @pytest.mark.anyio
    async def test_skips_when_empty_mapping(self) -> None:
        """Logs skipping when connectors mapping is empty."""
        job = _make_job()
        job.credential_mapping = {}
        mock_api = AsyncMock()
        semaphore = asyncio.Semaphore(5)

        await job._sync_connectors(mock_api, semaphore)

        mock_api.get_connector_cards.assert_not_called()
        job.logger.info.assert_called_with("No connectors in credential mapping. Skipping.")

    @pytest.mark.anyio
    async def test_syncs_connectors_success(self) -> None:
        """Successfully syncs connector parameters."""
        job = _make_job()
        job.credential_mapping = {"connectors": {"conn1": {"p1": "sec1:1"}}}
        job._secret_cache["sec1", "1"] = "secret-val-1"

        mock_api = AsyncMock()
        mock_api.get_connector_cards.return_value = {
            "connectorInstances": [{"displayName": "conn1", "identifier": "conn1-id"}]
        }
        semaphore = asyncio.Semaphore(5)

        await job._sync_connectors(mock_api, semaphore)

        mock_api.set_connector_parameter.assert_called_once_with(
            connector_instance_identifier="conn1-id",
            parameter_name="p1",
            parameter_value="secret-val-1",
        )
        assert len(job.execution_errors) == 0


class TestSyncJobs:
    """Tests for _sync_jobs."""

    @pytest.mark.anyio
    async def test_skips_when_empty_mapping(self) -> None:
        """Logs skipping when jobs mapping is empty."""
        job = _make_job()
        job.credential_mapping = {}
        mock_api = AsyncMock()
        semaphore = asyncio.Semaphore(5)

        await job._sync_jobs(mock_api, semaphore)

        mock_api.get_installed_jobs.assert_not_called()
        job.logger.info.assert_called_with("No jobs in credential mapping. Skipping.")

    @pytest.mark.anyio
    async def test_syncs_jobs_success(self) -> None:
        """Successfully syncs job parameters and saves."""
        job = _make_job()
        job.credential_mapping = {"jobs": {"Job A": {"API Key": "sec1:1"}}}
        job._secret_cache["sec1", "1"] = "secret-val-1"

        mock_api = AsyncMock()
        mock_api.get_installed_jobs.return_value = {
            "job_instances": [
                {
                    "displayName": "Job A",
                    "id": "1",
                    "parameters": [{"displayName": "API Key", "value": "old-val"}],
                }
            ]
        }
        semaphore = asyncio.Semaphore(5)

        await job._sync_jobs(mock_api, semaphore)

        mock_api.save_or_update_job.assert_called_once()
        assert len(job.execution_errors) == 0


class TestBuildJobNameLookup:
    """Tests for _build_job_name_lookup."""

    def test_uses_display_name(self) -> None:
        """Prefers 'displayName' key (1P format)."""
        job = _make_job()
        instances = [
            {"displayName": "Job A", "id": "1"},
            {"displayName": "Job B", "id": "2"},
        ]

        lookup = job._build_job_name_lookup(instances)

        assert lookup["Job A"]["id"] == "1"
        assert lookup["Job B"]["id"] == "2"

    def test_falls_back_to_name(self) -> None:
        """Uses 'name' key when 'displayName' is missing (Legacy)."""
        job = _make_job()
        instances = [{"name": "Legacy Job", "id": "3"}]

        lookup = job._build_job_name_lookup(instances)

        assert "Legacy Job" in lookup

    def test_empty_list(self) -> None:
        """Returns empty dict for empty input."""
        job = _make_job()
        lookup = job._build_job_name_lookup([])

        assert lookup == {}


class TestBuildParamIndex:
    """Tests for _build_param_index."""

    def test_builds_index(self) -> None:
        """Maps param display names to their list indices."""
        job = _make_job()
        params = [
            {"displayName": "API Key", "value": "x"},
            {"displayName": "Password", "value": "y"},
        ]

        index = job._build_param_index(params)

        assert index == {"API Key": 0, "Password": 1}

    def test_prefers_display_name_over_name(self) -> None:
        """Uses 'displayName' when both keys exist."""
        job = _make_job()
        params = [
            {"displayName": "Display", "name": "legacy", "value": "v"},
        ]

        index = job._build_param_index(params)

        assert "Display" in index
        assert "legacy" not in index


class TestSecretFetchCaching:
    """Tests for dictionary-based caching of secret fetches."""

    @pytest.mark.anyio
    async def test_caches_subsequent_fetches(self) -> None:
        """Only fetches once and uses cached payload for subsequent requests."""
        job = _make_job()

        mock_client = MagicMock()
        mock_client.get_secret_value.return_value = "secret-payload"
        job.akeyless_client = mock_client

        # First call
        val1 = await job._fetch_secret_value_pre_resolved(
            secret_id="secret-a",
            version_id="3",
            context_label="first call",
        )

        # Second call
        val2 = await job._fetch_secret_value_pre_resolved(
            secret_id="secret-a",
            version_id="3",
            context_label="second call",
        )

        assert val1 == "secret-payload"
        assert val2 == "secret-payload"

        mock_client.get_secret_value.assert_called_once_with(
            secret_id="secret-a",
            version_id="3",
        )

        assert job._secret_cache["secret-a", "3"] == "secret-payload"


class TestErrorAggregation:
    """Tests for error aggregation in the sync job."""

    @pytest.mark.anyio
    async def test_async_main_raises_on_errors(self) -> None:
        """Raises IntegrationCredentialSyncError if self.execution_errors is not empty."""
        job = _make_job()
        job.execution_errors = ["Some error occurred"]

        with (
            patch.object(job, "_init_akeyless_client"),
            patch("akeyless.jobs.sync_integration_credentials_job.AsyncChronicleSOAR") as mock_soar_cls,
            patch("akeyless.jobs.sync_integration_credentials_job.AsyncMarketplaceApi") as mock_market_cls,
        ):
            mock_soar = AsyncMock()
            mock_soar_cls.return_value = mock_soar
            mock_market = AsyncMock()
            mock_market_cls.return_value = mock_market

            # Mock sync functions to do nothing
            job._prefetch_all_secrets = AsyncMock()
            job._sync_integration_instances = AsyncMock()
            job._sync_connectors = AsyncMock()
            job._sync_jobs = AsyncMock()

            with pytest.raises(
                IntegrationCredentialSyncError,
                match="Sync completed with errors",
            ):
                await job._async_main()
