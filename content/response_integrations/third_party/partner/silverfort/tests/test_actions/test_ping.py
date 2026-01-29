"""Tests for Ping action."""

from __future__ import annotations

from integration_testing.platform.script_output import (  # type: ignore[import-not-found]
    MockActionOutput,
)
from integration_testing.set_meta import set_metadata  # type: ignore[import-not-found]
from TIPCommon.base.action import ExecutionState  # type: ignore[import-not-found]

from silverfort.actions import ping
from silverfort.tests.common import CONFIG_PATH
from silverfort.tests.core.product import MockSilverfort
from silverfort.tests.core.session import SilverfortSession


class TestPing:
    """Tests for the Ping action."""

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test successful ping with all APIs configured."""
        ping.main()

        # Verify requests were made
        assert len(script_session.request_history) >= 1

        # Verify successful output
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully connected" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        integration_config={
            "API Root": "https://mock-silverfort.local",
            "External API Key": "test-external-api-key",
            "Risk App User ID": "",
            "Risk App User Secret": "",
            "Service Accounts App User ID": "",
            "Service Accounts App User Secret": "",
            "Policies App User ID": "",
            "Policies App User Secret": "",
            "Verify SSL": True,
        },
    )
    def test_ping_no_credentials(
        self,
        script_session: SilverfortSession,
        action_output: MockActionOutput,
        silverfort: MockSilverfort,
    ) -> None:
        """Test ping fails when no API credentials configured."""
        ping.main()

        # Verify failure
        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "No API credentials configured" in action_output.results.output_message
