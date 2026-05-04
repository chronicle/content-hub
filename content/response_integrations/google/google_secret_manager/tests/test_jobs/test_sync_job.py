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

from unittest.mock import MagicMock, PropertyMock

import pytest

from google_secret_manager.core.constants import DEFAULT_SECRET_VERSION
from google_secret_manager.core.exceptions import (
    InvalidConfigurationError,
)
from google_secret_manager.jobs.sync_integration_credential_job import (
    SyncIntegrationCredentialJob,
)


def _make_job() -> SyncIntegrationCredentialJob:
    """Create a job instance with mocked SOAR internals."""
    job = SyncIntegrationCredentialJob.__new__(
        SyncIntegrationCredentialJob,
    )
    job.secret_manager_client = None
    job.credential_mapping = {}
    job.instance_name_to_identifier = {}
    job.connector_name_to_identifier = {}
    job.logger = MagicMock()

    # Mock self.params with attribute-style access.
    mock_params: MagicMock = MagicMock()
    mock_params.environment_name = "Default Environment"
    mock_params.credential_mapping = "{}"
    type(job).params = PropertyMock(return_value=mock_params)

    return job


# -------------------------------------------------------------------
# Credential Mapping Parsing
# -------------------------------------------------------------------


class TestParseCredentialMapping:
    """Tests for _parse_credential_mapping."""

    def test_valid_json(self) -> None:
        """Parses valid JSON credential mapping."""
        job = _make_job()
        job.params.credential_mapping = (
            '{"integration_instances": {"inst1": {}}}'
        )

        job._parse_credential_mapping()

        assert "integration_instances" in job.credential_mapping
        assert job.credential_mapping["integration_instances"] == {
            "inst1": {},
        }

    def test_valid_yaml(self) -> None:
        """Parses valid YAML credential mapping."""
        job = _make_job()
        job.params.credential_mapping = (
            "integration_instances:\n  inst1: {}\n"
        )

        job._parse_credential_mapping()

        assert "integration_instances" in job.credential_mapping

    def test_empty_mapping(self) -> None:
        """Empty string results in empty dict."""
        job = _make_job()
        job.params.credential_mapping = ""

        job._parse_credential_mapping()

        assert job.credential_mapping == {}

    def test_invalid_yaml_raises(self) -> None:
        """Raises InvalidConfigurationError on bad YAML."""
        job = _make_job()
        job.params.credential_mapping = "{{invalid: yaml: ["

        with pytest.raises(
            InvalidConfigurationError,
            match="Invalid Credential Mapping",
        ):
            job._parse_credential_mapping()


# -------------------------------------------------------------------
# Secret + Version Resolution
# -------------------------------------------------------------------


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
        job.secret_manager_client = mock_client

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
        job.secret_manager_client = None

        secret_id, version_id = job._resolve_secret_and_version(
            "my-secret",
        )

        assert secret_id == "my-secret"
        assert version_id == DEFAULT_SECRET_VERSION


# -------------------------------------------------------------------
# Job Lookup Helpers
# -------------------------------------------------------------------


class TestBuildJobNameLookup:
    """Tests for _build_job_name_lookup."""

    def test_uses_display_name(self) -> None:
        """Prefers 'displayName' key (1P format)."""
        instances = [
            {"displayName": "Job A", "id": "1"},
            {"displayName": "Job B", "id": "2"},
        ]

        lookup = SyncIntegrationCredentialJob._build_job_name_lookup(
            instances,
        )

        assert lookup["Job A"]["id"] == "1"
        assert lookup["Job B"]["id"] == "2"

    def test_falls_back_to_name(self) -> None:
        """Uses 'name' key when 'displayName' is missing (Legacy)."""
        instances = [{"name": "Legacy Job", "id": "3"}]

        lookup = SyncIntegrationCredentialJob._build_job_name_lookup(
            instances,
        )

        assert "Legacy Job" in lookup

    def test_empty_list(self) -> None:
        """Returns empty dict for empty input."""
        lookup = SyncIntegrationCredentialJob._build_job_name_lookup(
            [],
        )

        assert lookup == {}


class TestBuildParamIndex:
    """Tests for _build_param_index."""

    def test_builds_index(self) -> None:
        """Maps param display names to their list indices."""
        params = [
            {"displayName": "API Key", "value": "x"},
            {"displayName": "Password", "value": "y"},
        ]

        index = SyncIntegrationCredentialJob._build_param_index(
            params,
        )

        assert index == {"API Key": 0, "Password": 1}

    def test_prefers_display_name_over_name(self) -> None:
        """Uses 'displayName' when both keys exist."""
        params = [
            {"displayName": "Display", "name": "legacy", "value": "v"},
        ]

        index = SyncIntegrationCredentialJob._build_param_index(
            params,
        )

        assert "Display" in index
        assert "legacy" not in index
