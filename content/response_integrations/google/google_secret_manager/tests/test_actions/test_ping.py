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

"""Tests for the Ping action."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from google_secret_manager.actions import ping
from google_secret_manager.tests.common import CONFIG_PATH


class TestPing:
    """Tests for PingAction."""

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    @patch(
        "google.oauth2.service_account.Credentials.from_service_account_info",
    )
    @patch(
        "google.cloud.secretmanager.SecretManagerServiceClient",
    )
    def test_ping_success(
        self,
        mock_sm_cls: MagicMock,
        mock_sa_from_info: MagicMock,
        action_output: MockActionOutput,
    ) -> None:
        """Ping succeeds when test_connectivity returns True."""
        mock_instance: MagicMock = MagicMock()
        mock_sm_cls.return_value = mock_instance
        mock_instance.list_secrets.return_value = iter([])

        ping.main()

        mock_instance.list_secrets.assert_called_once()
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully connected" in (action_output.results.output_message)

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    @patch(
        "google.oauth2.service_account.Credentials.from_service_account_info",
    )
    @patch(
        "google.cloud.secretmanager.SecretManagerServiceClient",
    )
    def test_ping_failure(
        self,
        mock_sm_cls: MagicMock,
        mock_sa_from_info: MagicMock,
        action_output: MockActionOutput,
    ) -> None:
        """Ping reports failure when connectivity fails."""
        mock_instance: MagicMock = MagicMock()
        mock_sm_cls.return_value = mock_instance
        mock_instance.list_secrets.side_effect = Exception(
            "Connection refused",
        )

        ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
