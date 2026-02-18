"""Tests for GreyNoise Ping action."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from grey_noise.actions import ping
from grey_noise.tests.common import CONFIG_PATH
from grey_noise.tests.conftest import GreyNoiseSDK


def _get_future_expiration_date(years_ahead: int = 2) -> str:
    """Get a future expiration date to prevent API key expiration errors in tests.

    Args:
        years_ahead: Number of years to add to current date (default: 2)

    Returns:
        Date string in YYYY-MM-DD format
    """
    future_date = datetime.now() + timedelta(days=365 * years_ahead)
    return future_date.strftime("%Y-%m-%d")


class TestPing:
    """Test class for Ping action."""

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success_vip_key(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test successful ping operation with VIP API key using authentic SDK response."""
        # Use authentic VIP response from captured data
        greynoise_sdk.set_test_connection_response({
            "expiration": _get_future_expiration_date(),
            "message": "pong",
            "offering": "vip",
            "address": "103.108.207.58",
        })

        ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success_community_key(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test successful ping operation with community API key."""
        greynoise_sdk.set_test_connection_response({
            "expiration": _get_future_expiration_date(),
            "message": "pong",
            "offering": "community",
            "address": "103.108.207.58",
        })

        ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_success_enterprise_key(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test successful ping operation with enterprise API key."""
        greynoise_sdk.set_test_connection_response({
            "expiration": _get_future_expiration_date(),
            "message": "pong",
            "offering": "enterprise",
            "address": "103.108.207.58",
        })

        ping.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_invalid_api_key(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test ping with invalid API key."""
        greynoise_sdk.simulate_test_connection_failure(should_fail=True)

        ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_request_failure(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test ping with RequestFailure exception (auth error)."""
        # Mock the SDK to raise RequestFailure
        from greynoise.exceptions import RequestFailure

        greynoise_sdk.ping = MagicMock(side_effect=RequestFailure("401 Client Error"))

        ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to connect to the GreyNoise server" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH)
    def test_ping_general_exception(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test ping with general exception."""
        # Mock the SDK to raise a general exception
        greynoise_sdk.ping = MagicMock(side_effect=Exception("Connection timeout"))

        ping.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Connection timeout" in action_output.results.output_message
