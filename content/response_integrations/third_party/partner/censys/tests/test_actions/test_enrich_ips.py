from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from censys.actions import enrich_ips
from censys.tests.common import CONFIG_PATH, REPUTATION_MULTI_IP_BATCH
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
        censys_manager.set_enrich_hosts_response(
            {
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
            }
        )

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
        censys_manager.set_enrich_hosts_response(
            {
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
            }
        )

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched 2 IP(s)" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "1.1.4.3",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_reputation_fields_in_json_output(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """HostDatamodel (Get Host API) previously extracted no reputation
        data at all. Reputation must now flow through into the JSON case
        wall output, matching the Get Host Enrichment API behavior."""
        censys_manager.set_enrich_hosts_response(
            {
                "result": [
                    {
                        "resource": {
                            "ip": "1.1.4.3",
                            "services": [],
                            "reputation": {
                                "label": "BENIGN",
                                "score": 0.191,
                                "score_suppressed": False,
                                "class_probabilities": [
                                    {"label": "BENIGN", "probability": 0.6899},
                                ],
                                "evidence": [
                                    {
                                        "feature": {
                                            "id": "max_port",
                                            "name": "Max Port",
                                            "contribution": 0.047,
                                            "category": "service_surface",
                                        }
                                    }
                                ],
                            },
                        }
                    }
                ]
            }
        )

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

        json_result = action_output.results.json_output.json_result
        entity_result = json_result[0]["EntityResult"]
        reputation = entity_result["result"]["resource"]["reputation"]
        assert reputation["label"] == "BENIGN"
        assert reputation["evidence"][0]["feature"]["id"] == "max_port"

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "1.1.4.3",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_ips_null_reputation_does_not_crash(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Regression guard: Censys can return explicit JSON null for the
        reputation sub-object. This must not raise and the action should
        still complete successfully.

        location.country is included so the host produces other enrichment
        data - otherwise the entity would be classified "not found" for
        having no enrichment data at all, which would mask whether the null
        reputation itself was handled safely.
        """
        censys_manager.set_enrich_hosts_response(
            {
                "result": [
                    {
                        "resource": {
                            "ip": "1.1.4.3",
                            "location": {"country": "United States"},
                            "services": [],
                            "reputation": None,
                        }
                    }
                ]
            }
        )

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True

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
        assert (
            "No ADDRESS type entities found in scope"
            in action_output.results.output_message
        )

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
        assert (
            "No valid IP addresses to process" in action_output.results.output_message
        )

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
        censys_manager.simulate_enrich_hosts_failure(
            should_fail=True, exception_type="generic"
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
        censys_manager.simulate_enrich_hosts_failure(
            should_fail=True, exception_type="rate_limit"
        )

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
        censys_manager.set_enrich_hosts_response(
            {
                "result": [
                    {
                        "resource": {
                            "ip": "8.8.8.8",
                            "location": {"country": "United States"},
                            "services": [],
                        }
                    }
                ]
            }
        )

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
        censys_manager.set_enrich_hosts_response(
            {
                "result": [
                    {
                        "resource": {
                            "ip": "8.8.8.8",
                            "location": {"country": "United States"},
                            "services": [],
                        }
                    }
                ]
            }
        )

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
        censys_manager.simulate_enrich_hosts_failure(
            should_fail=True, exception_type="validation"
        )

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Validation error" in action_output.results.output_message


class TestEnrichIpsMultiIpMixedReputationBatch:
    """One case with 4 IPs in a single execution: full reputation, missing
    optional fields, no reputation key, and explicit null reputation. Runs
    through the real action main() end-to-end (not just the datamodel layer)
    to prove the batch API-response-matching and entity update logic handles
    a mixed reputation batch correctly."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "198.51.100.1",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            },
            {
                "identifier": "198.51.100.2",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            },
            {
                "identifier": "198.51.100.3",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            },
            {
                "identifier": "198.51.100.4",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            },
        ],
    )
    def test_all_four_ips_enrich_with_only_two_getting_reputation_data(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        resources = [
            REPUTATION_MULTI_IP_BATCH["ip_a_full"]["result"]["resource"],
            REPUTATION_MULTI_IP_BATCH["ip_b_missing_fields"]["result"]["resource"],
            REPUTATION_MULTI_IP_BATCH["ip_c_no_reputation"]["result"]["resource"],
            REPUTATION_MULTI_IP_BATCH["ip_d_null_reputation"]["result"]["resource"],
        ]
        censys_manager.set_enrich_hosts_response(
            {"result": [{"resource": r} for r in resources]}
        )

        enrich_ips.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched 4 IP(s)" in action_output.results.output_message

        json_result = action_output.results.json_output.json_result
        entities_by_ip = {
            entry["Entity"]: entry["EntityResult"]["result"]["resource"]
            for entry in json_result
        }
        assert set(entities_by_ip) == {
            "198.51.100.1",
            "198.51.100.2",
            "198.51.100.3",
            "198.51.100.4",
        }

        # Only the two IPs with reputation data carry a reputation object
        # through to the JSON output; the other two still enriched (they
        # have location/ASN), just with no reputation key/null.
        assert entities_by_ip["198.51.100.1"]["reputation"]["label"] == "MALICIOUS"
        assert "label" not in entities_by_ip["198.51.100.2"]["reputation"]
        assert "reputation" not in entities_by_ip["198.51.100.3"]
        assert entities_by_ip["198.51.100.4"]["reputation"] is None
