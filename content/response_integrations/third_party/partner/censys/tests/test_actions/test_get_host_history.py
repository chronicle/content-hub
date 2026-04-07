from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from censys.actions.get_host_history import main
from censys.tests.common import CONFIG_PATH, HOST_HISTORY_RESPONSE
from censys.tests.conftest import CensysAPIManager


class TestHostHistory:
    """Test class for Enrich Web Properties action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
        parameters={
            "Host ID": "8.8.8.8",
            "Start Time": "2025-01-01T00:00:00Z",
            "End Time": "2026-01-01T00:00:00Z ",
        },
    )
    def test_host_history_api_failures(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test Invalid Host History."""
        censys_manager.simulate_host_history_failure(
            should_fail=True, exception_type="generic"
        )
        main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
        parameters={"Host ID": "443", "Start Time": "dede", "End Time": "ded"},
    )
    def test_host_history_invalid_inputs(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test Invalid Host History."""
        main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Invalid Host ID: 443" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
        parameters={
            "Host ID": "8.8.8.8",
            "Start Time": "2025-01-01T00:00:00Z",
            "End Time": "2026-01-01T00:00:00Z ",
        },
    )
    def test_host_history_not_found(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test Invalid Host History."""
        censys_manager.set_host_history_response({})
        main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert (
            "No historical data found for host 8.8.8.8 within the specified time range."
            in action_output.results.output_message
        )

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
        parameters={
            "Host ID": "8.8.8.8",
            "Start Time": "2025-01-01T00:00:00Z",
            "End Time": "2026-01-01T00:00:00Z ",
        },
    )
    def test_host_history_success(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test Invalid Host History."""
        censys_manager.set_host_history_response(HOST_HISTORY_RESPONSE)
        main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert (
            "Successfully retrieved 2 event(s) for host 8.8.8.8."
            in action_output.results.output_message
        )
