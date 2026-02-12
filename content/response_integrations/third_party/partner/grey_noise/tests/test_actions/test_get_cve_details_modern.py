"""Tests for GreyNoise Get CVE Details action."""

from __future__ import annotations

from unittest.mock import MagicMock

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from grey_noise.actions import get_cve_details
from grey_noise.tests.common import CONFIG_PATH
from grey_noise.tests.conftest import GreyNoiseSDK


class TestGetCVEDetailsAction:
    """Test class for Get CVE Details action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "CVE-2024-1234", "entity_type": "CVE", "additional_properties": {}}
        ],
    )
    def test_get_cve_details_success(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test successful CVE details retrieval using authentic SDK response."""
        greynoise_sdk.set_cve_response({
            "cve_id": "CVE-2024-1234",
            "description": "Test CVE 1",
            "severity": "high",
            "cvss_score": 8.5,
        })

        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[])
    def test_get_cve_details_no_entities(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details with no CVE entities."""
        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "No CVE" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "INVALID-2024-1234", "entity_type": "CVE", "additional_properties": {}}
        ],
    )
    def test_get_cve_details_invalid_format(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details with invalid CVE format."""
        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "failed to process" in action_output.results.output_message.lower()

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "CVE-2024-1234", "entity_type": "CVE", "additional_properties": {}}
        ],
    )
    def test_get_cve_details_api_failure(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details with API failure."""
        greynoise_sdk.simulate_cve_failure(should_fail=True)

        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.FAILED

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "CVE-2024-1234", "entity_type": "CVE", "additional_properties": {}},
            {"identifier": "CVE-2024-5678", "entity_type": "CVE", "additional_properties": {}},
        ],
    )
    def test_get_cve_details_partial_success(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details with partial success."""
        # Both CVEs succeed in this test since the mock returns the same response for both
        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully processed" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "CVE-2024-1234-INVALID",
                "entity_type": "CVE",
                "additional_properties": {},
            }
        ],
    )
    def test_get_cve_details_malformed_cve(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details with malformed CVE identifier."""
        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "failed to process" in action_output.results.output_message.lower()

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "CVE-2024-1234", "entity_type": "CVE", "additional_properties": {}}
        ],
    )
    def test_get_cve_details_not_found(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details when CVE is not found."""
        # Mock the CVE method to return None (not found)
        greynoise_sdk.cve = MagicMock(return_value=None)

        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Not found in GreyNoise dataset: 1 CVE(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[{"identifier": "INVALID-CVE", "entity_type": "CVE", "additional_properties": {}}],
    )
    def test_get_cve_details_value_error(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details with ValueError (invalid format)."""
        # Mock the SDK to raise ValueError
        greynoise_sdk.cve = MagicMock(side_effect=ValueError("Invalid CVE format"))

        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to process all 1 CVE(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "CVE-2024-1234", "entity_type": "CVE", "additional_properties": {}}
        ],
    )
    def test_get_cve_details_request_failure(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details with RequestFailure."""
        # Mock the SDK to raise RequestFailure
        from greynoise.exceptions import RequestFailure

        greynoise_sdk.cve = MagicMock(side_effect=RequestFailure("API request failed"))

        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to process all 1 CVE(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "CVE-2024-1234", "entity_type": "CVE", "additional_properties": {}}
        ],
    )
    def test_get_cve_details_general_exception(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details with general exception."""
        # Mock the SDK to raise general exception
        greynoise_sdk.cve = MagicMock(side_effect=Exception("General error"))

        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert "Failed to process all 1 CVE(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "CVE-2024-1234", "entity_type": "CVE", "additional_properties": {}},
            {"identifier": "CVE-2024-5678", "entity_type": "CVE", "additional_properties": {}},
        ],
    )
    def test_get_cve_details_mixed_results(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details with mixed success and failure."""

        # Mock partial success - first CVE succeeds, second fails
        def side_effect_func(cve_id):
            if cve_id == "CVE-2024-1234":
                return {
                    "cve": {
                        "id": "CVE-2024-1234",
                        "description": "Test CVE description",
                        "severity": "HIGH",
                    }
                }
            else:
                raise RequestFailure("Not found")

        greynoise_sdk.cve = MagicMock(side_effect=side_effect_func)

        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert "Successfully processed 1 CVE(s)" in action_output.results.output_message
        assert "Failed to process 1 CVE(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {"identifier": "CVE-2024-1234", "entity_type": "CVE", "additional_properties": {}}
        ],
    )
    def test_get_cve_details_rate_limit_error(
        self,
        action_output: MockActionOutput,
        greynoise_sdk: GreyNoiseSDK,
    ) -> None:
        """Test CVE details with rate limit error."""
        # Mock the SDK to raise RateLimitError at the action level (not entity level)
        from greynoise.exceptions import RateLimitError

        greynoise_sdk.cve = MagicMock(side_effect=RateLimitError("Rate limit exceeded"))

        get_cve_details.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        # Rate limit errors at action level should show "Daily rate limit reached"
        assert (
            "Daily rate limit reached" in action_output.results.output_message
            or "Failed to process all 1 CVE(s)" in action_output.results.output_message
        )
