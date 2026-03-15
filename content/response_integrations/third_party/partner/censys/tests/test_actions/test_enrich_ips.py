from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from censys.actions import enrich_ips
from censys.tests.common import CONFIG_PATH
from censys.tests.conftest import CensysAPIManager


class TestEnrichIPs:
    """Test class for Enrich IPs action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_success(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test successful IP enrichment with single entity."""
        censys_manager.set_enrich_hosts_response({
            "result": [
                {
                    "resource": {
                        "ip": "8.8.8.8",
                        "location": {
                            "country": "United States",
                            "country_code": "US",
                            "city": "Mountain View",
                        },
                        "autonomous_system": {
                            "asn": 15169,
                            "name": "GOOGLE",
                        },
                        "services": [
                            {
                                "port": 443,
                                "service_name": "HTTPS",
                                "transport_protocol": "TCP",
                            }
                        ],
                    }
                }
            ]
        })

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched 1 IP(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            },
            {
                "identifier": "1.1.1.1",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            },
        ],
    )
    def test_enrich_ips_multiple_entities(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test successful IP enrichment with multiple entities."""
        censys_manager.set_enrich_hosts_response({
            "result": [
                {
                    "resource": {
                        "ip": "8.8.8.8",
                        "location": {"country": "United States"},
                        "autonomous_system": {"asn": 15169},
                        "services": [],
                    }
                },
                {
                    "resource": {
                        "ip": "1.1.1.1",
                        "location": {"country": "Australia"},
                        "autonomous_system": {"asn": 13335},
                        "services": [],
                    }
                },
            ]
        })

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched 2 IP(s)" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[])
    def test_enrich_ips_no_entities(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test IP enrichment with no entities."""
        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "No ADDRESS type entities found in scope" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_not_found(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test IP enrichment when IP not found in Censys."""
        censys_manager.set_enrich_hosts_response({"result": []})

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "not found in Censys" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "invalid_ip",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_invalid_ip_format(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test IP enrichment with invalid IP format."""
        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "No valid IP addresses to process" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_api_failure(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test IP enrichment with API failure."""
        censys_manager.simulate_enrich_hosts_failure(should_fail=True, exception_type="generic")

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_unauthorized(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test IP enrichment with unauthorized error."""
        censys_manager.simulate_enrich_hosts_failure(
            should_fail=True, exception_type="unauthorized"
        )

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_rate_limit(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test IP enrichment with rate limit error."""
        censys_manager.simulate_enrich_hosts_failure(should_fail=True, exception_type="rate_limit")

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"At Time": "2024-01-15T10:30:00Z"},
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_with_at_time(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test IP enrichment with historical timestamp."""
        censys_manager.set_enrich_hosts_response({
            "result": [
                {
                    "resource": {
                        "ip": "8.8.8.8",
                        "location": {"country": "United States"},
                        "services": [],
                    }
                }
            ]
        })

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched 1 IP(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        parameters={"At Time": "invalid_timestamp"},
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_invalid_timestamp(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test IP enrichment with invalid timestamp format."""
        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Invalid parameter value" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            },
            {
                "identifier": "1.1.1.1",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            },
        ],
    )
    def test_enrich_ips_partial_success(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test IP enrichment with partial success (one found, one not found)."""
        censys_manager.set_enrich_hosts_response({
            "result": [
                {
                    "resource": {
                        "ip": "8.8.8.8",
                        "location": {"country": "United States"},
                        "services": [],
                    }
                }
            ]
        })

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched 1 IP(s)" in action_output.results.output_message
        assert "not found in Censys" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_validation_error(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test IP enrichment with validation error."""
        censys_manager.simulate_enrich_hosts_failure(should_fail=True, exception_type="validation")

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Validation error" in action_output.results.output_message
