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

# ruff: noqa: S105, S106
import time
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from akeyless.core.constants import DEFAULT_SECRET_VERSION
from akeyless.core.exceptions import (
    IntegrationCredentialSyncError,
    InvalidConfigurationError,
)
from akeyless.jobs.sync_integration_credential_job import (
    SyncIntegrationCredentialJob,
)


def _make_job() -> SyncIntegrationCredentialJob:
    """Create a job instance with mocked SOAR internals."""
    job = SyncIntegrationCredentialJob.__new__(
        SyncIntegrationCredentialJob,
    )
    job.akeyless_client = None
    job.credential_mapping = {}
    job.instance_name_to_identifier = {}
    job.connector_name_to_identifier = {}
    job.name_id = "SyncIntegrationCredentialJob"
    job.state_context = {}
    job._secret_cache = {}
    job._sync_errors = []
    job._job_start_time = int(time.time() * 1000)
    type(job).logger = PropertyMock(return_value=MagicMock())

    # Mock self.params with attribute-style access.
    mock_params: MagicMock = MagicMock()
    mock_params.environment_name = "Default Environment"
    mock_params.credential_mapping = "{}"
    type(job).params = PropertyMock(return_value=mock_params)

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

    def test_valid_yaml(self) -> None:
        """Parses valid YAML credential mapping."""
        job = _make_job()
        job.params.credential_mapping = "integration_instances:\n  inst1: {}\n"

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
        """Splits on first colon only: 'a:b:c' → ('a', 'b:c')."""
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


class TestStateContextRegistry:
    """Tests for persistent state context registry and skipping logic."""

    def test_load_context_success(self) -> None:
        """Loads valid JSON context state from soar_job."""
        job = _make_job()
        mock_soar_job = MagicMock()
        mock_soar_job.get_job_context_property.return_value = '{"instance:id1:p1": "secret:1::10"}'
        type(job).soar_job = PropertyMock(return_value=mock_soar_job)

        job._load_context()

        assert job.state_context == {"instance:id1:p1": "secret:1::10"}

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
        job.state_context = {"instance:id1:p1": "secret:1::10"}

        job._save_context()

        mock_soar_job.set_job_context_property.assert_called_once_with(
            identifier=job.name_id,
            property_key="sync_credentials_state",
            property_value='{"instance:id1:p1": "secret:1::10"}',
        )

    @pytest.mark.anyio
    async def test_set_integration_params_does_not_skip_when_up_to_date(self) -> None:
        """Verify that we do not skip fetching and setting configuration when parameter is up-to-date."""
        job = _make_job()
        job.state_context = {"instance:inst_id:param_x": "my-secret::5"}

        mock_client = MagicMock()
        mock_client.resolve_latest_enabled_version.return_value = "5"
        job.akeyless_client = mock_client

        job._fetch_secret_value_pre_resolved = AsyncMock(return_value="cached-secret-val")

        mock_api = AsyncMock()

        await job._set_integration_params(
            api=mock_api,
            name="Instance A",
            identifier="inst_id",
            param_mapping={"param_x": "my-secret"},
        )

        job._fetch_secret_value_pre_resolved.assert_called_once_with(
            "my-secret", "5", context_label="param 'param_x' on instance 'Instance A' (id: inst_id)"
        )
        mock_api.set_configuration_property.assert_called_once_with(
            integration_instance_identifier="inst_id",
            property_name="param_x",
            property_value="cached-secret-val",
        )

    @pytest.mark.anyio
    async def test_set_integration_params_updates_when_outdated(self) -> None:
        """Updates and saves to context when parameter is outdated."""
        job = _make_job()
        job.state_context = {"instance:inst_id:param_x": "my-secret:latest::5"}

        mock_client = MagicMock()
        mock_client.resolve_latest_enabled_version.return_value = "6"
        job.akeyless_client = mock_client

        job._fetch_secret_value_pre_resolved = AsyncMock(return_value="new-secret-value")

        mock_api = AsyncMock()

        await job._set_integration_params(
            api=mock_api,
            name="Instance A",
            identifier="inst_id",
            param_mapping={"param_x": "my-secret"},
        )

        job._fetch_secret_value_pre_resolved.assert_called_once_with(
            "my-secret", "6", context_label="param 'param_x' on instance 'Instance A' (id: inst_id)"
        )
        mock_api.set_configuration_property.assert_called_once_with(
            integration_instance_identifier="inst_id",
            property_name="param_x",
            property_value="new-secret-value",
        )
        assert job.state_context["instance:inst_id:param_x"] == "my-secret::6"


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
        """Raises IntegrationCredentialSyncError if self._sync_errors is not empty."""
        job = _make_job()
        job._sync_errors = ["Some error occurred"]

        with (
            patch.object(job, "_init_akeyless_client"),
            patch.object(job, "_load_context"),
            patch.object(job, "_save_context"),
            patch("akeyless.jobs.sync_integration_credential_job.AsyncChronicleSOAR") as mock_soar_cls,
            patch("akeyless.jobs.sync_integration_credential_job.AsyncMarketplaceApi") as mock_market_cls,
        ):
            mock_soar = AsyncMock()
            mock_soar_cls.return_value = mock_soar
            mock_market = AsyncMock()
            mock_market_cls.return_value = mock_market

            # Mock sync functions to do nothing
            job._sync_integration_instances = AsyncMock()
            job._sync_connectors = AsyncMock()
            job._sync_jobs = AsyncMock()

            with pytest.raises(
                IntegrationCredentialSyncError,
                match="Credential synchronization completed with one or more errors",
            ):
                await job._async_main()
