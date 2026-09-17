from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from censys.actions import enrich_host
from censys.tests.common import CONFIG_PATH
from censys.tests.conftest import CensysAPIManager


class TestEnrichHost:
    """Test class for Enrich Host action."""

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
    def test_enrich_host_success(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test successful host enrichment with single entity."""
        censys_manager.set_enrich_host_response(
            {
                "result": {
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
                                "protocol": "HTTPS",
                            }
                        ],
                        "reputation": {
                            "score": 12,
                            "score_level": "benign",
                        },
                        "privacy": [
                            {
                                "tor": False,
                                "vpn": False,
                                "proxy": False,
                                "anonymous": False,
                                "relay": False,
                            }
                        ],
                        "third_party": {
                            "mallory": [
                                {
                                    "last_seen_at": "2026-07-20T09:14:32Z",
                                    "observable": {
                                        "name": "dns.google",
                                        "type": "host",
                                        "description": "Google Public DNS",
                                    },
                                    "opinions": [
                                        {
                                            "confidence": "high",
                                            "description": "Observed as public DNS infrastructure",
                                            "source": "mallory",
                                            "verdict": "benign",
                                            "updated_at": "2026-07-20T09:14:32Z",
                                        }
                                    ],
                                }
                            ]
                        },
                    }
                }
            }
        )

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched 1 host(s)" in action_output.results.output_message

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
    def test_enrich_host_multiple_entities(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test successful host enrichment with multiple entities, each a separate call."""
        censys_manager.set_enrich_host_response_for_ip(
            "8.8.8.8",
            {
                "result": {
                    "resource": {
                        "ip": "8.8.8.8",
                        "location": {"country": "United States"},
                        "autonomous_system": {"asn": 15169},
                        "services": [],
                    }
                }
            },
        )
        censys_manager.set_enrich_host_response_for_ip(
            "1.1.1.1",
            {
                "result": {
                    "resource": {
                        "ip": "1.1.1.1",
                        "location": {"country": "Australia"},
                        "autonomous_system": {"asn": 13335},
                        "services": [],
                    }
                }
            },
        )

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched 2 host(s)" in action_output.results.output_message

    @set_metadata(integration_config_file_path=CONFIG_PATH, entities=[])
    def test_enrich_host_no_entities(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test host enrichment with no entities."""
        enrich_host.main()

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
    def test_enrich_host_not_found(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test host enrichment when host not found in Censys (empty resource)."""
        censys_manager.set_enrich_host_response({"result": {"resource": {}}})

        enrich_host.main()

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
    def test_enrich_host_invalid_ip_format(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test host enrichment with invalid IP format."""
        enrich_host.main()

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
    def test_enrich_host_api_failure(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test host enrichment with API failure - reported as a per-entity failure."""
        censys_manager.simulate_enrich_host_failure(
            should_fail=True, exception_type="generic"
        )

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "failed to process" in action_output.results.output_message

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
    def test_enrich_host_unauthorized(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test host enrichment with unauthorized error - broken credentials affect
        the whole integration, so this fails like every other action."""
        censys_manager.simulate_enrich_host_failure(
            should_fail=True, exception_type="unauthorized"
        )

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message
        assert "failed to process" not in action_output.results.output_message

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
    def test_enrich_host_forbidden(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test host enrichment when the account has no access to the new endpoint (403)."""
        censys_manager.simulate_enrich_host_failure(
            should_fail=True, exception_type="forbidden"
        )

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message
        assert "permission" in action_output.results.output_message

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
    def test_enrich_host_feature_not_enabled(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test host enrichment when the enrichment feature isn't enabled for the account tier (409)."""
        censys_manager.simulate_enrich_host_failure(
            should_fail=True, exception_type="feature_not_enabled"
        )

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message
        assert "Feature not enabled" in action_output.results.output_message

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
    def test_enrich_host_daily_quota_reached(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test host enrichment when the daily request quota is exhausted (429) -
        quota is integration-wide, not endpoint-specific, so this fails like
        every other action."""
        censys_manager.simulate_enrich_host_failure(
            should_fail=True, exception_type="rate_limit"
        )

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message
        assert "failed to process" not in action_output.results.output_message

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
    def test_enrich_host_not_found_via_404(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test that a 404 from the API is treated as 'not found', not a failure."""
        censys_manager.simulate_enrich_host_failure(
            should_fail=True, exception_type="not_found"
        )

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "not found in Censys" in action_output.results.output_message
        assert "failed to process" not in action_output.results.output_message

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
            {
                "identifier": "9.9.9.9",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            },
        ],
    )
    def test_enrich_host_account_level_error_aborts_remaining_ips(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test that an account-level error (403) mid-loop stops further processing,
        reports the skip, and fails the action overall even though one IP was
        already enriched before the error occurred."""
        censys_manager.set_enrich_host_response_for_ip(
            "8.8.8.8",
            {
                "result": {
                    "resource": {
                        "ip": "8.8.8.8",
                        "location": {"country": "United States"},
                        "services": [],
                    }
                }
            },
        )
        censys_manager.simulate_enrich_host_failure_for_ip("1.1.1.1", "forbidden")

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "1 host(s) were already enriched" in action_output.results.output_message
        # The IP that triggered the account-level error (1.1.1.1) and the one
        # after it (9.9.9.9, never attempted) both land in "skipped" - neither
        # got a clean success/not_found/failed outcome.
        assert "2 host(s) were not attempted and were skipped" in (
            action_output.results.output_message
        )
        assert "1.1.1.1" in action_output.results.output_message
        assert "9.9.9.9" in action_output.results.output_message

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
    def test_enrich_host_partial_success(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test host enrichment with partial success (one found, one not found)."""
        censys_manager.set_enrich_host_response_for_ip(
            "8.8.8.8",
            {
                "result": {
                    "resource": {
                        "ip": "8.8.8.8",
                        "location": {"country": "United States"},
                        "services": [],
                    }
                }
            },
        )
        censys_manager.set_enrich_host_response_for_ip(
            "1.1.1.1", {"result": {"resource": {}}}
        )

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched 1 host(s)" in action_output.results.output_message
        assert "not found in Censys" in action_output.results.output_message

    @set_metadata(
        integration_config={
            "API Key": "test_api_key_12345",
            "Organization Id": "test_org_id_67890",
            "Verify SSL": "false",
            "Enable Get Host Enrichment API": "false",
        },
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_host_new_api_disabled(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test that the action short-circuits when the new API is disabled for this instance."""
        censys_manager.set_enrich_host_response(
            {"result": {"resource": {"ip": "8.8.8.8", "services": []}}}
        )

        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "disabled" in action_output.results.output_message.lower()

    @set_metadata(
        integration_config={
            "API Key": "test_api_key_12345",
            "Organization Id": "test_org_id_67890",
            "Verify SSL": "false",
        },
        entities=[
            {
                "identifier": "8.8.8.8",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_host_new_api_defaults_to_disabled(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test that the new API is disabled by default when not configured on the instance."""
        enrich_host.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "disabled" in action_output.results.output_message.lower()
