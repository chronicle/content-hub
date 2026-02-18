"""Tests for GreyNoise Execute GNQL Query action."""

from __future__ import annotations

from unittest.mock import MagicMock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from grey_noise.actions import execute_gnql_query
from grey_noise.tests.common import CONFIG_PATH
from grey_noise.tests.conftest import GreyNoiseSDK

# Action-specific configuration
ACTION_CONFIG_PATH = "tests/test_actions/execute_gnql_query_config.json"


class TestExecuteGNQLQuery:
    """Test class for Execute GNQL Query action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "classification:malicious",
            "Max Results": "100",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_success(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test successful GNQL query execution using authentic SDK response."""
        greynoise_sdk.set_gnql_response({
            "data": [
                {"ip": "192.168.1.100", "classification": "malicious", "actor": "MaliciousActor"},
                {"ip": "10.0.0.50", "classification": "malicious", "actor": "EvilBot"},
            ],
            "request_metadata": {"count": 2, "complete": True, "scroll": ""},
        })

        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "classification:malicious",
            "Max Results": "100",
            "Quick": False,
            "Exclude Raw": True,
        },
        entities=[],
    )
    def test_execute_gnql_query_no_entities(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution - GNQL doesn't require entities, should work without them."""
        greynoise_sdk.set_gnql_response({
            "data": [
                {"ip": "192.168.1.100", "classification": "malicious", "actor": "MaliciousActor"}
            ],
            "request_metadata": {"count": 1, "complete": True, "scroll": ""},
        })

        execute_gnql_query.main()

        # GNQL Query should work without entities
        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "classification:malicious",
            "Max Results": "100",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_api_failure(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution with API failure."""
        greynoise_sdk.simulate_gnql_failure(should_fail=True)

        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "   ",  # Whitespace only
            "Max Results": "100",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_empty_query(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution with empty query (whitespace only)."""
        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "GNQL Query parameter is required" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "classification:malicious",
            "Max Results": "100",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_rate_limit_error(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution with rate limit error."""
        # Mock the SDK to raise RateLimitError
        from greynoise.exceptions import RateLimitError

        greynoise_sdk.query = MagicMock(side_effect=RateLimitError("Rate limit exceeded"))

        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Rate limit reached" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "classification:malicious",
            "Max Results": "100",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_request_failure_401(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution with 401 RequestFailure."""
        # Mock the SDK to raise RequestFailure with 401 error
        from greynoise.exceptions import RequestFailure

        greynoise_sdk.query = MagicMock(side_effect=RequestFailure("401 Client Error"))

        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to connect to the GreyNoise server" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "classification:malicious",
            "Max Results": "100",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_general_exception(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution with general exception."""
        # Mock the SDK to raise a general exception
        greynoise_sdk.query = MagicMock(side_effect=Exception("Connection error"))

        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Connection error" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "classification:malicious",
            "Max Results": "1",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_max_results_limit(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution with max results limit."""
        # Mock response with more data than max_results
        greynoise_sdk.set_gnql_response({
            "data": [
                {"ip": "192.168.1.100", "classification": "malicious"},
                {"ip": "10.0.0.50", "classification": "malicious"},
            ],
            "request_metadata": {"count": 2, "complete": False, "scroll": "abc123"},
        })

        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        # Should limit results to max_results (1 in this case)

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "nonexistent:field",
            "Max Results": "100",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_empty_results(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution with empty results."""
        # Mock response with no data
        greynoise_sdk.set_gnql_response({
            "data": [],
            "request_metadata": {"count": 0, "complete": True, "scroll": ""},
        })

        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "No IP addresses match the query criteria" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "classification:malicious",
            "Max Results": "100",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_request_failure_general(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution with general RequestFailure (non-401)."""
        # Mock the SDK to raise RequestFailure with non-401 error
        from greynoise.exceptions import RequestFailure

        greynoise_sdk.query = MagicMock(side_effect=RequestFailure("500 Server Error"))

        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to connect to the GreyNoise server" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "classification:malicious",
            "Max Results": "invalid",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_invalid_integer_exception(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution with invalid integer parameter."""
        # Mock the SDK to raise InvalidIntegerException
        from grey_noise.core.greynoise_exceptions import InvalidIntegerException

        greynoise_sdk.query = MagicMock(
            side_effect=InvalidIntegerException("Invalid integer value for Max Results")
        )

        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Max Results must be an integer" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={
            "GNQL Query": "classification:malicious",
            "Max Results": "100",
            "Quick": False,
            "Exclude Raw": True,
        },
    )
    def test_execute_gnql_query_value_error(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test GNQL query execution with ValueError."""
        # Mock the SDK to raise ValueError
        greynoise_sdk.query = MagicMock(side_effect=ValueError("Invalid parameter"))

        execute_gnql_query.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Invalid parameter value: Invalid parameter" in action_output.results.output_message
