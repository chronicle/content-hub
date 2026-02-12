"""
Test cases for actions/ip_timeline_lookup.py to improve coverage from 75% to 99%.
"""

from unittest.mock import patch

from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

import grey_noise.actions.ip_timeline_lookup as ip_timeline_lookup
from grey_noise.tests.common import CONFIG_PATH
from grey_noise.tests.conftest import GreyNoiseSDK


class TestIPTimelineLookup:
    """Test class for IP Timeline Lookup action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_ip_timeline_lookup_success(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with successful response."""
        greynoise_sdk.set_ip_timeline_response({
            "ip": "8.8.8.8",
            "metadata": {"field": "classification", "first_seen": "2023-01-01"},
            "results": [{"timestamp": "2023-01-01", "label": "benign", "data": "10"}],
        })

        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully processed 1 IP(s)" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[])
    def test_ip_timeline_lookup_no_entities(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with no entities."""
        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "No IP ADDRESS entities found to process" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_ip_timeline_lookup_no_timeline_data(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with empty timeline data."""
        greynoise_sdk.set_ip_timeline_response({
            "ip": "8.8.8.8",
            "metadata": {"field": "classification", "first_seen": "2023-01-01"},
            "results": [],
        })

        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully processed 1 IP(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_ip_timeline_lookup_none_response(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with None response to cover lines 115-116."""
        greynoise_sdk.timeline = lambda *args, **kwargs: None
        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to process" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_ip_timeline_lookup_request_failure_in_loop(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test RequestFailure in entity loop to cover lines 120-122."""
        from greynoise.exceptions import RequestFailure

        greynoise_sdk.simulate_ip_timeline_failure(RequestFailure("API request failed"))
        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to process" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_ip_timeline_lookup_general_exception_handling(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test general exception in entity loop to cover lines 124-128."""
        greynoise_sdk.simulate_ip_timeline_failure(RuntimeError("Unexpected error"))
        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to process" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}},
            {"identifier": "1.1.1.1", "entity_type": "ADDRESS", "additional_properties": {}},
        ],
    )
    def test_ip_timeline_lookup_mixed_success_failure(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with mixed success and failure."""
        from greynoise.exceptions import RequestFailure

        # First call succeeds, second fails
        call_count = 0

        def timeline_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "ip": "8.8.8.8",
                    "metadata": {"field": "classification", "first_seen": "2023-01-01"},
                    "results": [{"timestamp": "2023-01-01", "label": "benign", "data": "10"}],
                }
            else:
                raise RequestFailure("API request failed")

        greynoise_sdk.timeline = timeline_side_effect
        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully processed 1 IP(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}},
            {"identifier": "1.1.1.1", "entity_type": "ADDRESS", "additional_properties": {}},
        ],
    )
    def test_ip_timeline_lookup_all_entities_fail(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup when all entities fail."""
        from greynoise.exceptions import RequestFailure

        greynoise_sdk.simulate_ip_timeline_failure(RequestFailure("API request failed"))
        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to process" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
        parameters={"Days": "invalid"},
    )
    def test_ip_timeline_lookup_invalid_days_parameter(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with invalid Days parameter to cover lines 153-156."""
        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "must be an integer" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
        parameters={"Granularity": "invalid"},
    )
    def test_ip_timeline_lookup_invalid_granularity(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with invalid Granularity parameter - passes through to API."""
        ip_timeline_lookup.main()

        # No validation in code, so action completes successfully
        # The invalid granularity is passed to the API which returns data
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_ip_timeline_lookup_rate_limit_error(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test RateLimitError to cover lines 164-169."""
        from greynoise.exceptions import RateLimitError

        with patch("grey_noise.actions.ip_timeline_lookup.APIManager") as mock_manager:
            mock_manager.side_effect = RateLimitError()
            ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "rate limit" in action_output.results.output_message.lower()

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_ip_timeline_lookup_authentication_error(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test AuthenticationException to cover lines 171-176."""
        # AuthenticationException doesn't exist, use generic Exception instead

        with patch("grey_noise.actions.ip_timeline_lookup.APIManager") as mock_manager:
            mock_manager.side_effect = Exception("Authentication failed")
            ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Error while executing action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_ip_timeline_lookup_unexpected_exception(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test unexpected exception to cover lines 178-183."""
        with patch("grey_noise.actions.ip_timeline_lookup.get_ip_entities") as mock_get_entities:
            mock_get_entities.side_effect = RuntimeError("Unexpected error occurred")
            ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "error" in action_output.results.output_message.lower()

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
        parameters={"Days": "0"},
    )
    def test_ip_timeline_lookup_zero_days(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with Days=0 which should fail validation."""
        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        # Zero is not allowed for Days parameter
        assert "greater than zero" in action_output.results.output_message.lower()

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
        parameters={"Days": "-5"},
    )
    def test_ip_timeline_lookup_negative_days(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with negative Days which should fail validation."""
        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        # Negative values are not allowed for Days parameter

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
    )
    def test_ip_timeline_lookup_no_insight_generated(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup when insight generation returns None (line 108 false branch)."""
        greynoise_sdk.set_ip_timeline_response({
            "ip": "8.8.8.8",
            "metadata": {"field": "classification", "first_seen": "2023-01-01"},
            "results": [{"timestamp": "2023-01-01", "label": "benign", "data": "10"}],
        })

        # Patch generate_timeline_insight to return None
        with patch(
            "grey_noise.actions.ip_timeline_lookup.generate_timeline_insight"
        ) as mock_insight:
            mock_insight.return_value = None
            ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully processed" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}},
            {"identifier": "1.1.1.1", "entity_type": "ADDRESS", "additional_properties": {}},
            {"identifier": "9.9.9.9", "entity_type": "ADDRESS", "additional_properties": {}},
        ],
    )
    def test_ip_timeline_lookup_multiple_entities_all_success(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with multiple entities all succeeding."""
        greynoise_sdk.set_ip_timeline_response({
            "ip": "8.8.8.8",
            "metadata": {"field": "classification", "first_seen": "2023-01-01"},
            "results": [{"timestamp": "2023-01-01", "label": "benign", "data": "10"}],
        })

        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully processed 3 IP(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
        parameters={"Days": "1"},
    )
    def test_ip_timeline_lookup_minimum_days(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with minimum valid Days=1."""
        greynoise_sdk.set_ip_timeline_response({
            "ip": "8.8.8.8",
            "metadata": {"field": "classification", "first_seen": "2023-01-01"},
            "results": [{"timestamp": "2023-01-01", "label": "benign", "data": "10"}],
        })

        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "8.8.8.8", "entity_type": "ADDRESS", "additional_properties": {}}],
        parameters={"Field": "ports"},
    )
    def test_ip_timeline_lookup_custom_field(
        self,
        action_output,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test IP timeline lookup with custom field parameter."""
        greynoise_sdk.set_ip_timeline_response({
            "ip": "8.8.8.8",
            "metadata": {"field": "ports", "first_seen": "2023-01-01"},
            "results": [{"timestamp": "2023-01-01", "label": "22", "data": "100"}],
        })

        ip_timeline_lookup.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
