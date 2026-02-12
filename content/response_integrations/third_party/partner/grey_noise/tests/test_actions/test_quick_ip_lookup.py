"""Tests for GreyNoise Quick IP Lookup action."""

from __future__ import annotations

from unittest.mock import MagicMock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from grey_noise.actions import quick_ip_lookup
from grey_noise.tests.common import CONFIG_PATH
from grey_noise.tests.conftest import GreyNoiseSDK


class TestQuickIPLookup:
    """Test class for Quick IP Lookup action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_quick_ip_lookup_success(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test successful quick IP lookup with authentic SDK response."""
        greynoise_sdk.set_quick_ip_response([
            {
                "ip": "8.8.8.8",
                "noise": True,
                "riot": False,
                "classification": "benign",
                "trust_level": "1",
                "name": "Google Public DNS",
                "category": "public_dns",
                "last_seen": "2025-12-26T13:11:04Z",
            }
        ])

        quick_ip_lookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[])
    def test_quick_ip_lookup_no_entities(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test quick IP lookup with no IP entities."""
        quick_ip_lookup.main()

        # Quick IP Lookup completes when no entities are found
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "No IP ADDRESS entities found to process" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_quick_ip_lookup_api_failure(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test quick IP lookup with API failure."""
        greynoise_sdk.simulate_quick_ip_failure(should_fail=True)

        quick_ip_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_quick_ip_lookup_rate_limit_error(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test quick IP lookup with rate limit error."""
        # Mock the SDK to raise RateLimitError
        from greynoise.exceptions import RateLimitError

        greynoise_sdk.quick = MagicMock(side_effect=RateLimitError("Rate limit exceeded"))

        quick_ip_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Rate limit reached" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_quick_ip_lookup_request_failure(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test quick IP lookup with RequestFailure."""
        # Mock the SDK to raise RequestFailure
        from greynoise.exceptions import RequestFailure

        greynoise_sdk.quick = MagicMock(side_effect=RequestFailure("401 Client Error"))

        quick_ip_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to connect to the GreyNoise server" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_quick_ip_lookup_general_exception(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test quick IP lookup with general exception."""
        # Mock the SDK to raise a general exception
        greynoise_sdk.quick = MagicMock(side_effect=Exception("Connection error"))

        quick_ip_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Connection error" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_quick_ip_lookup_entity_enrichment(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test quick IP lookup with entity enrichment."""
        # Use the existing mock setup with noise=True to trigger enrichment path
        greynoise_sdk.set_quick_ip_response([
            {"ip": "8.8.8.8", "noise": True, "riot": False, "classification": "benign"}
        ])

        quick_ip_lookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        # Should complete successfully and may include enrichment info
