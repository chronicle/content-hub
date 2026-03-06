from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from censys.actions import enrich_web_properties
from censys.tests.common import CONFIG_PATH
from censys.tests.conftest import CensysAPIManager


class TestEnrichWebProperties:
    """Test class for Enrich Web Properties action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "example.com",
                "entity_type": "DOMAIN",
                "additional_properties": {},
            }
        ],
        parameters={"Ports": "443"},
    )
    def test_enrich_web_properties_success(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test successful web property enrichment."""
        censys_manager.set_enrich_web_properties_response({
            "result": [
                {
                    "resource": {
                        "webproperty_id": "example.com:443",
                        "hostname": "example.com",
                        "port": 443,
                        "http": {
                            "response": {
                                "status_code": 200,
                                "headers": {"Server": "nginx"},
                            }
                        },
                    }
                }
            ]
        })

        enrich_web_properties.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
        parameters={"Ports": "443"},
    )
    def test_enrich_web_properties_no_entities(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test web property enrichment with no entities."""
        enrich_web_properties.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "No ADDRESS or HOSTNAME type entities found" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "example.com",
                "entity_type": "DOMAIN",
                "additional_properties": {},
            }
        ],
        parameters={"Ports": "443"},
    )
    def test_enrich_web_properties_not_found(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test web property enrichment when not found."""
        censys_manager.set_enrich_web_properties_response({"result": []})

        enrich_web_properties.main()

        # Action completes but with no enrichment
        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "not found in Censys" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "example.com",
                "entity_type": "DOMAIN",
                "additional_properties": {},
            }
        ],
        parameters={"Ports": "443"},
    )
    def test_enrich_web_properties_api_failure(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test web property enrichment with API failure."""
        censys_manager.simulate_enrich_web_properties_failure(
            should_fail=True, exception_type="generic"
        )

        enrich_web_properties.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "example.com",
                "entity_type": "DOMAIN",
                "additional_properties": {},
            }
        ],
        parameters={"Port": "99999"},
    )
    def test_enrich_web_properties_invalid_port(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test web property enrichment with invalid port (out of range)."""
        enrich_web_properties.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Invalid parameter value" in action_output.results.output_message
