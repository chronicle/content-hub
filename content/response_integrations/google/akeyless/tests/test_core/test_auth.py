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

from akeyless.core.auth import (
    IntegrationParameters,
    build_auth_params,
)
from akeyless.core.constants import (
    INTEGRATION_IDENTIFIER,
    ACCESS_ID_PARAM,
    ACCESS_KEY_PARAM,
    ACCESS_TYPE_PARAM,
    API_GATEWAY_URL_PARAM,
)
from akeyless.core.exceptions import (
    AkeylessError,
)


class TestBuildAuthParams:
    """Tests for the build_auth_params factory function."""

    def test_action_extracts_from_configuration(self) -> None:
        """For SiemplifyAction, reads from get_configuration()."""
        mock_action: MagicMock = MagicMock()
        mock_action.__class__.__name__ = "SiemplifyAction"
        mock_action.get_configuration.return_value = {
            ACCESS_ID_PARAM: "test-access-id",
            ACCESS_KEY_PARAM: "test-access-key",
            ACCESS_TYPE_PARAM: "access_key",
            API_GATEWAY_URL_PARAM: "https://api.akeyless.io",
        }

        result: IntegrationParameters = build_auth_params(mock_action)

        mock_action.get_configuration.assert_called_once_with(
            INTEGRATION_IDENTIFIER,
        )
        assert result.access_id == "test-access-id"
        assert result.access_key == "test-access-key"
        assert result.access_type == "access_key"
        assert result.api_gateway_url == "https://api.akeyless.io"

    def test_job_extracts_from_parameters(self) -> None:
        """For SiemplifyJob, reads from .parameters dict."""
        mock_job: MagicMock = MagicMock()
        mock_job.__class__.__name__ = "SiemplifyJob"
        mock_job.parameters = {
            ACCESS_ID_PARAM: "test-access-id",
            ACCESS_KEY_PARAM: "test-access-key",
            ACCESS_TYPE_PARAM: "access_key",
            API_GATEWAY_URL_PARAM: "https://api.akeyless.io",
        }

        result: IntegrationParameters = build_auth_params(mock_job)

        assert result.access_id == "test-access-id"
        assert result.access_key == "test-access-key"
        assert result.access_type == "access_key"
        assert result.api_gateway_url == "https://api.akeyless.io"

    def test_unsupported_type_raises(self) -> None:
        """Raises AkeylessError for unknown SDK types."""
        mock_unknown: MagicMock = MagicMock()
        mock_unknown.__class__.__name__ = "UnknownSDKClass"

        with pytest.raises(
            AkeylessError,
            match="not supported",
        ):
            build_auth_params(mock_unknown)
