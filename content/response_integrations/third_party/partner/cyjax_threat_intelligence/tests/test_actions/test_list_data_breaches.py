"""Tests for CYJAX Threat Intelligence List Data Breaches action."""

from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyjax_threat_intelligence.actions import list_data_breaches
from cyjax_threat_intelligence.tests.common import (
    CONFIG_PATH,
    MOCK_LIST_DATA_BREACHES_RESPONSE,
)
from cyjax_threat_intelligence.tests.core.product import CyjaxThreatIntelligence
from cyjax_threat_intelligence.tests.core.session import CyjaxSession

DEFAULT_PARAMETERS = {
    "Query": "test",
    "Since": "2024-01-01T00:00:00Z",
}


class TestListDataBreaches:
    """Test class for List Data Breaches action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
    )
    def test_list_data_breaches_success(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test successful data breaches retrieval."""
        cyjax.list_data_breaches_response = MOCK_LIST_DATA_BREACHES_RESPONSE
        success_output_msg_prefix = "Successfully retrieved"

        list_data_breaches.main()

        assert len(script_session.request_history) >= 1
        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
    )
    def test_list_data_breaches_api_failure(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test data breaches with API failure."""
        cyjax.should_fail_list_data_breaches = True

        list_data_breaches.main()

        assert action_output.results.result_value is False
        assert action_output.results.execution_state.value == 2
        assert (
            "Failed" in action_output.results.output_message
            or "Error" in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Query": "test"},
    )
    def test_list_data_breaches_without_since(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test data breaches without Since parameter."""
        cyjax.list_data_breaches_response = MOCK_LIST_DATA_BREACHES_RESPONSE

        list_data_breaches.main()

        assert len(script_session.request_history) >= 1
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters=DEFAULT_PARAMETERS,
    )
    def test_list_data_breaches_empty_response(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test data breaches with empty response."""
        cyjax.list_data_breaches_response = []

        list_data_breaches.main()

        assert len(script_session.request_history) >= 1

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "Query": "credentials",
            "Since": "2024-01-01T00:00:00Z",
            "Until": "2024-12-31T23:59:59Z",
        },
    )
    def test_list_data_breaches_with_until(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test data breaches with Until parameter."""
        cyjax.list_data_breaches_response = MOCK_LIST_DATA_BREACHES_RESPONSE
        success_output_msg_prefix = "Successfully retrieved"

        list_data_breaches.main()

        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Query": ""},
    )
    def test_list_data_breaches_empty_query(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test data breaches with empty query."""
        list_data_breaches.main()

        # Should handle empty query gracefully
