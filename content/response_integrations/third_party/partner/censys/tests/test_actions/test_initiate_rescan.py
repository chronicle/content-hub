from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from censys.actions import initiate_rescan
from censys.tests.common import CONFIG_PATH
from censys.tests.conftest import CensysAPIManager


class TestInitiateRescan:
    """Test class for Initiate Rescan action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "IOC Type": "Service",
            "IOC Value": "8.8.8.8",
            "Port": "443",
            "Protocol": "HTTPS",
            "Transport Protocol": "TCP",
        },
    )
    def test_initiate_rescan_success_host(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test successful rescan initiation for host."""
        censys_manager.set_initiate_rescan_response({
            "result": {
                "tracked_scan_id": "scan_12345",
                "tasks": [],
                "create_time": "2024-01-15T10:30:00Z",
            }
        })

        initiate_rescan.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "scan_12345" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "IOC Type": "Web Origin",
            "IOC Value": "example.com",
            "Port": "443",
        },
    )
    def test_initiate_rescan_success_web_properties(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test successful rescan initiation for web properties."""
        censys_manager.set_initiate_rescan_response({
            "result": {
                "tracked_scan_id": "scan_67890",
                "tasks": [],
                "create_time": "2024-01-15T10:30:00Z",
            }
        })

        initiate_rescan.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "scan_67890" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "IOC Type": "Service",
            "IOC Value": "8.8.8.8",
            "Port": "443",
            "Protocol": "HTTPS",
            "Transport Protocol": "TCP",
        },
    )
    def test_initiate_rescan_api_failure(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test rescan initiation with API failure."""
        censys_manager.simulate_initiate_rescan_failure(should_fail=True, exception_type="generic")

        initiate_rescan.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "IOC Type": "Service",
            "IOC Value": "8.8.8.8",
            "Port": "443",
            "Protocol": "HTTPS",
            "Transport Protocol": "TCP",
        },
    )
    def test_initiate_rescan_unauthorized(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test rescan initiation with unauthorized error."""
        censys_manager.simulate_initiate_rescan_failure(
            should_fail=True, exception_type="unauthorized"
        )

        initiate_rescan.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "IOC Type": "Service",
            "IOC Value": "8.8.8.8",
            "Port": "443",
            "Protocol": "HTTPS",
            "Transport Protocol": "TCP",
        },
    )
    def test_initiate_rescan_validation_error(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test rescan initiation with validation error."""
        censys_manager.simulate_initiate_rescan_failure(
            should_fail=True, exception_type="validation"
        )

        initiate_rescan.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
