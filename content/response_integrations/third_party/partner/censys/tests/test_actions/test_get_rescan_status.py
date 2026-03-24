from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from censys.actions import get_rescan_status
from censys.tests.common import CONFIG_PATH
from censys.tests.conftest import CensysAPIManager


class TestGetRescanStatus:
    """Test class for Get Rescan Status action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Scan ID": "scan_12345"},
    )
    def test_get_rescan_status_success(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test successful rescan status retrieval."""
        censys_manager.set_rescan_status_response({
            "result": {
                "tracked_scan_id": "scan_12345",
                "completed": True,
                "tasks": [
                    {
                        "task_id": "task_001",
                        "status": "completed",
                        "result": "success",
                    }
                ],
                "completed_at": "2024-01-15T10:35:00Z",
            }
        })

        get_rescan_status.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "completed" in action_output.results.output_message.lower()

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Scan ID": "scan_12345"},
    )
    def test_get_rescan_status_pending(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test rescan status retrieval for pending scan."""
        censys_manager.set_rescan_status_response({
            "result": {
                "tracked_scan_id": "scan_12345",
                "tasks": [],
            }
        })

        get_rescan_status.main()

        # Scan without 'completed' field should be IN_PROGRESS
        assert action_output.results.execution_state.value == 1  # IN_PROGRESS
        assert action_output.results.result_value is True

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Scan ID": "scan_12345"},
    )
    def test_get_rescan_status_api_failure(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test rescan status retrieval with API failure."""
        censys_manager.simulate_rescan_status_failure(should_fail=True, exception_type="generic")

        get_rescan_status.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"Scan ID": "   "},
    )
    def test_get_rescan_status_missing_scan_id(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test rescan status retrieval with empty scan ID (whitespace only)."""
        get_rescan_status.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Scan ID must be a non-empty string" in action_output.results.output_message
