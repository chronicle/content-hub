from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata
from TIPCommon.base.action import ExecutionState

from censys.actions import enrich_certificates
from censys.tests.common import CONFIG_PATH
from censys.tests.conftest import CensysAPIManager


class TestEnrichCertificates:
    """Test class for Enrich Certificates action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "a" * 64,
                "entity_type": "FILEHASH",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_certificates_success(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test successful certificate enrichment."""
        censys_manager.set_enrich_certificates_response({
            "result": [
                {
                    "resource": {
                        "fingerprint_sha256": "a" * 64,
                        "parsed": {
                            "subject_dn": "CN=example.com",
                            "issuer_dn": "CN=Let's Encrypt Authority X3",
                            "validity": {
                                "start": "2024-01-01T00:00:00Z",
                                "end": "2024-12-31T23:59:59Z",
                            },
                        },
                    }
                }
            ]
        })

        enrich_certificates.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "Successfully enriched" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
    )
    def test_enrich_certificates_no_entities(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test certificate enrichment with no entities."""
        enrich_certificates.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is True
        assert "No FILEHASH type entities found" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "b" * 64,
                "entity_type": "FILEHASH",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_certificates_not_found(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test certificate enrichment when not found."""
        censys_manager.set_enrich_certificates_response({"result": []})

        enrich_certificates.main()

        assert action_output.results.execution_state == ExecutionState.COMPLETED
        assert action_output.results.result_value is False
        assert "not found in Censys" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "c" * 64,
                "entity_type": "FILEHASH",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_certificates_api_failure(
        self,
        action_output: MockActionOutput,
        censys_manager: CensysAPIManager,
    ) -> None:
        """Test certificate enrichment with API failure."""
        censys_manager.simulate_enrich_certificates_failure(
            should_fail=True, exception_type="generic"
        )

        enrich_certificates.main()

        assert action_output.results.execution_state == ExecutionState.FAILED
        assert action_output.results.result_value is False
        assert "Error while executing action" in action_output.results.output_message
