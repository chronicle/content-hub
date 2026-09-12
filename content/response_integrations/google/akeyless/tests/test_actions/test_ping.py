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

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from akeyless.actions import ping
from akeyless.tests.common import CONFIG_PATH

if TYPE_CHECKING:
    from integration_testing.platform.script_output import MockActionOutput


class TestPing:
    """Tests for PingAction."""

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    @patch("akeyless.core.manager.AkeylessClient.test_connectivity")
    def test_ping_success(
        self,
        mock_test_connectivity: MagicMock,
        action_output: MockActionOutput,
    ) -> None:
        """Ping succeeds when test_connectivity returns True."""
        mock_test_connectivity.return_value = True

        ping.main()

        mock_test_connectivity.assert_called_once()
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully connected" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    @patch("akeyless.core.manager.AkeylessClient.test_connectivity")
    def test_ping_failure(
        self,
        mock_test_connectivity: MagicMock,
        action_output: MockActionOutput,
    ) -> None:
        """Ping reports failure when connectivity fails."""
        mock_test_connectivity.side_effect = Exception("Connection refused")

        ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
