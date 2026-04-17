"""Tests for CYJAX Threat Intelligence Enrich IOCs action."""

from __future__ import annotations

from integration_testing.platform.script_output import MockActionOutput
from integration_testing.set_meta import set_metadata

from cyjax_threat_intelligence.actions import enrich_iocs
from cyjax_threat_intelligence.tests.common import (
    CONFIG_PATH,
    MOCK_ENRICH_IOCS_RESPONSE,
)
from cyjax_threat_intelligence.tests.core.product import CyjaxThreatIntelligence
from cyjax_threat_intelligence.tests.core.session import CyjaxSession

DEFAULT_ENTITIES = [
    {
        "identifier": "1.1.1.1",
        "entity_type": "ADDRESS",
        "additional_properties": {},
    },
    {
        "identifier": "8.8.8.8",
        "entity_type": "ADDRESS",
        "additional_properties": {},
    },
]


class TestEnrichIOCs:
    """Test class for Enrich IOCs action."""

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=DEFAULT_ENTITIES,
    )
    def test_enrich_iocs_success(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test successful IOC enrichment."""
        cyjax.enrich_iocs_response = MOCK_ENRICH_IOCS_RESPONSE
        success_output_msg_prefix = "Successfully enriched"

        enrich_iocs.main()

        assert len(script_session.request_history) >= 1
        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[],
    )
    def test_enrich_iocs_no_entities(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test enrichment with no entities."""
        enrich_iocs.main()

        assert (
            "No entities found" in action_output.results.output_message
            or "No suitable entities" in action_output.results.output_message
        )
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=DEFAULT_ENTITIES,
    )
    def test_enrich_iocs_api_failure(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test enrichment with API failure - action handles partial failures gracefully."""
        cyjax.should_fail_enrich_iocs = True

        enrich_iocs.main()

        # Action returns True even when all IOCs fail, with a message about failures
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0
        assert "No IOCs were successfully enriched" in action_output.results.output_message
        assert "Failed to enrich" in action_output.results.output_message

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=[
            {
                "identifier": "1.1.1.1",
                "entity_type": "ADDRESS",
                "additional_properties": {},
            }
        ],
    )
    def test_enrich_iocs_single_entity(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test enrichment with single entity."""
        cyjax.enrich_iocs_response = MOCK_ENRICH_IOCS_RESPONSE
        success_output_msg_prefix = "Successfully enriched"

        enrich_iocs.main()

        assert success_output_msg_prefix in action_output.results.output_message
        assert action_output.results.result_value is True
        assert action_output.results.execution_state.value == 0

    @set_metadata(
        integration_config_file_path=CONFIG_PATH,
        entities=DEFAULT_ENTITIES,
    )
    def test_enrich_iocs_empty_response(
        self,
        script_session: CyjaxSession,
        action_output: MockActionOutput,
        cyjax: CyjaxThreatIntelligence,
    ) -> None:
        """Test enrichment with empty API response."""
        cyjax.enrich_iocs_response = {}

        enrich_iocs.main()

        assert len(script_session.request_history) >= 1
