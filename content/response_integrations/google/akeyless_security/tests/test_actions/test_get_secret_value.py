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

"""Tests for the Get Secret Value action."""

from __future__ import annotations

# ruff:file-ignore[hardcoded-password-func-arg]
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from akeyless.exceptions import ApiException
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from akeyless_security.actions import get_secret_value
from akeyless_security.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput


class TestGetSecretValue:
    """Tests for GetSecretValueAction."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Secret Name": "/prod/db/password"},
    )
    @patch("akeyless_security.core.manager.AkeylessClient.get_secret_value")
    def test_get_secret_value_default_version_success(
        self,
        mock_get_secret_value: MagicMock,
        action_output: MockActionOutput,
    ) -> None:
        """Fetches secret with default 'latest' version and sets JSON result."""
        mock_get_secret_value.return_value = "super-secret-val"

        get_secret_value.main()

        mock_get_secret_value.assert_called_once_with(
            secret_id="/prod/db/password",
            version_id="latest",
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully retrieved secret '/prod/db/password'" in action_output.results.output_message
        assert action_output.results.json_output.json_result == {
            "secret_name": "/prod/db/password",
            "version": "latest",
            "secret_value": "super-secret-val",
        }

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Secret Name": "/prod/db/password:3"},
    )
    @patch("akeyless_security.core.manager.AkeylessClient.get_secret_value")
    def test_get_secret_value_explicit_version_success(
        self,
        mock_get_secret_value: MagicMock,
        action_output: MockActionOutput,
    ) -> None:
        """Parses 'secret_name:version' and fetches the specified secret version."""
        mock_get_secret_value.return_value = "v3-secret-val"

        get_secret_value.main()

        mock_get_secret_value.assert_called_once_with(
            secret_id="/prod/db/password",
            version_id="3",
        )
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert action_output.results.json_output.json_result == {
            "secret_name": "/prod/db/password",
            "version": "3",
            "secret_value": "v3-secret-val",
        }

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Secret Name": ":invalid-secret-format"},
    )
    def test_get_secret_value_invalid_format_fails(
        self,
        action_output: MockActionOutput,
    ) -> None:
        """Fails gracefully when Secret Name does not match the expected format."""
        get_secret_value.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Invalid credential mapping format" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Secret Name": "/prod/missing-secret"},
    )
    def test_get_secret_value_api_error_strips_headers(
        self,
        mock_akeyless_api: MagicMock,
        action_output: MockActionOutput,
    ) -> None:
        """Parses API error body cleanly and omits raw HTTP response headers."""
        mock_akeyless_api.auth.return_value = MagicMock(token="tok-123")
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.reason = "Not Found"
        mock_resp.data = '{"error":"item /prod/missing-secret was not found"}'
        mock_resp.getheaders.return_value = {"Content-Security-Policy": "long-csp"}
        mock_akeyless_api.get_secret_value.side_effect = ApiException(http_resp=mock_resp)

        get_secret_value.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "item /prod/missing-secret was not found" in action_output.results.output_message
        assert "HTTP response headers" not in action_output.results.output_message
