"""Tests for CYJAX Threat Intelligence Domain Monitor action."""

from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyjax_threat_intelligence.actions import domain_monitor
from cyjax_threat_intelligence.tests.common import (
    CONFIG_PATH,
    MOCK_DOMAIN_MONITOR_RESPONSE,
)
from cyjax_threat_intelligence.tests.core.product import CyjaxThreatIntelligence
from cyjax_threat_intelligence.tests.core.session import CyjaxSession

DEFAULT_PARAMETERS = {
    "Query": "example.com",
    "Since": "2024-01-01T00:00:00Z",
}


class TestDomainMonitor:
    """Test class for Domain Monitor action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
    )
    def test_domain_monitor_success(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test successful domain monitor retrieval."""
        cyjax.domain_monitor_response = MOCK_DOMAIN_MONITOR_RESPONSE
        success_output_msg_prefix = "Successfully retrieved"

        domain_monitor.main()

        assert len(script_session.request_history) >= 1
        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
    )
    def test_domain_monitor_api_failure(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test domain monitor with API failure."""
        cyjax.should_fail_domain_monitor = True

        domain_monitor.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
        assert (
            "Failed" in action_output.results.output_message
            or "Error" in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Query": "example.com"},
    )
    def test_domain_monitor_without_since(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test domain monitor without Since parameter."""
        cyjax.domain_monitor_response = MOCK_DOMAIN_MONITOR_RESPONSE

        domain_monitor.main()

        assert len(script_session.request_history) >= 1
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
    )
    def test_domain_monitor_empty_response(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test domain monitor with empty response."""
        cyjax.domain_monitor_response = []

        domain_monitor.main()

        assert len(script_session.request_history) >= 1

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Query": "test.com",
            "Since": "2024-01-01T00:00:00Z",
            "Until": "2024-12-31T23:59:59Z",
        },
    )
    def test_domain_monitor_with_until(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test domain monitor with Until parameter."""
        cyjax.domain_monitor_response = MOCK_DOMAIN_MONITOR_RESPONSE
        success_output_msg_prefix = "Successfully retrieved"

        domain_monitor.main()

        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
