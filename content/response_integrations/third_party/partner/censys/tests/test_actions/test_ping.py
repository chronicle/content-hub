from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from censys.actions import ping
from censys.tests.common import CONFIG_PATH
from censys.tests.conftest import CensysAPIManager


class TestPing:
    """Test class for Ping action."""

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test successful ping operation."""
        censys_manager.set_connectivity_response(True)

        ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully connected to the Censys" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_unauthorized(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test ping with unauthorized error (invalid credentials)."""
        censys_manager.simulate_connectivity_failure(
            should_fail=True, exception_type="unauthorized"
        )

        ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Failed to connect to the Censys" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_rate_limit(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test ping with rate limit error."""
        censys_manager.simulate_connectivity_failure(should_fail=True, exception_type="rate_limit")

        ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Failed to connect to the Censys" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_http_error(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test ping with HTTP error (500)."""
        censys_manager.simulate_connectivity_failure(should_fail=True, exception_type="http_error")

        ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Failed to connect to the Censys" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_generic_exception(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test ping with generic exception."""
        censys_manager.exception_message = "Connection timeout"
        censys_manager.simulate_connectivity_failure(should_fail=True, exception_type="generic")

        ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Failed to connect to the Censys" in action_output.results.output_message
