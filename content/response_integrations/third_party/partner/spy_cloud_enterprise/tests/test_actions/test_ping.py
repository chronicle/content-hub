"""Tests for SpyCloud Enterprise Ping action."""

from __future__ import annotations

from unittest.mock import MagicMock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from spy_cloud_enterprise.actions import Ping
from spy_cloud_enterprise.tests.common import CONFIG_PATH


class TestPing:
    """Test class for the Ping connectivity action."""

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        action_output: MockActionOutput,
        spycloud_sdk: MagicMock,
    ) -> None:
        """A successful breach catalog ping completes the action."""
        spycloud_sdk.breach_catalog.ping.return_value = True

        Ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value == "true"

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_failure(
        self,
        action_output: MockActionOutput,
        spycloud_sdk: MagicMock,
    ) -> None:
        """A failed breach catalog ping fails the action."""
        spycloud_sdk.breach_catalog.ping.side_effect = Exception(
            "Unable to connect to SpyCloud breach catalog"
        )

        Ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value == "false"
