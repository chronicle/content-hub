"""Tests for CYJAX Threat Intelligence Ping action."""

from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyjax_threat_intelligence.actions import ping
from cyjax_threat_intelligence.tests.common import (
    CONFIG_PATH,
    MOCK_PING_RESPONSE,
)
from cyjax_threat_intelligence.tests.core.product import CyjaxThreatIntelligence
from cyjax_threat_intelligence.tests.core.session import CyjaxSession


class TestPing:
    """Test class for Ping action."""

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test successful ping operation."""
        cyjax.ping_response = MOCK_PING_RESPONSE
        success_output_msg = "Successfully connected to the Cyjax server!"

        ping.main()

        assert len(script_session.request_history) >= 1
        assert action_output.results.output_message == success_output_msg
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_api_failure(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test ping with API failure."""
        cyjax.ping_response = None
        cyjax.should_fail_ping = True

        ping.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
        assert (
            "Failed" in action_output.results.output_message
            or "Error" in action_output.results.output_message
        )

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_empty_response(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test ping with empty response."""
        cyjax.ping_response = []

        ping.main()

        # Empty response should still be considered successful if API responds
        assert len(script_session.request_history) >= 1
