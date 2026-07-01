from __future__ import annotations

from unittest.mock import MagicMock

from actions.EnrichIndicator import (
    SCRIPT_NAME,
    EnrichIndicator,
    EnrichIndicatorParameters,
)
from core.opencti_client.client import OpenCTIClientError
from core.opencti_client.enrich_results import IndicatorEnrichmentResult


def _make_entity(identifier: str, entity_type: str = "ADDRESS") -> MagicMock:
    entity = MagicMock()
    entity.entity_type = entity_type
    entity.identifier = identifier
    entity.original_identifier = identifier
    entity.additional_properties = {}
    entity.is_enriched = False
    entity.is_suspicious = False
    return entity


def _indicator_result(
    identifier: str = "1.2.3.4",
    score: int = 85,
    found: bool = True,
    confidence: int | None = 90,
    relationships: list[dict] | None = None,
    kill_chain_phases: list[dict] | None = None,
) -> IndicatorEnrichmentResult | None:
    if not found:
        return None
    return IndicatorEnrichmentResult(
        id="indicator--abc123",
        x_opencti_score=score,
        name=identifier,
        confidence=confidence,
        valid_from="2025-01-01T00:00:00.000Z",
        valid_until="2026-12-31T23:59:59.000Z",
        pattern=f"[ipv4-addr:value = '{identifier}']",
        labelObject=["malicious"],
        killChainPhases=kill_chain_phases
        or [{"kill_chain_name": "mitre-attack", "phase_name": "command-and-control"}],
        link="https://opencti.example.com/dashboard/id/indicator--abc123",
        relationships=relationships or [],
    )


class TestEnrichIndicatorParameters:
    def test_defaults(self):
        params = EnrichIndicatorParameters()
        assert params.threshold == 50
        assert params.create_insight is True

    def test_custom_values(self):
        params = EnrichIndicatorParameters(threshold=70, create_insight=False)
        assert params.threshold == 70
        assert params.create_insight is False


class TestEnrichIndicatorAction:
    def test_validate_params_reads_threshold_and_insight(self, mock_soar_enrich_action):
        mock_soar_enrich_action.parameters = {"Threshold": 70, "Create Insight": False}
        action = EnrichIndicator(SCRIPT_NAME)
        action._validate_params()
        assert action.params.threshold == 70
        assert action.params.create_insight is False

    def test_unsupported_entity_types_are_skipped(
        self, mock_soar_enrich_action, mock_api_client
    ):
        mock_soar_enrich_action.parameters = {}
        mock_soar_enrich_action.target_entities = [
            _make_entity("CVE-2024-1234", "CVE"),
            _make_entity("EvilGroup", "THREATACTOR"),
        ]
        action = EnrichIndicator(SCRIPT_NAME)
        action.run()
        mock_api_client.enrich_indicator.assert_not_called()
        assert action.result_value is False
        assert "supported entity types" in action.output_message

    def test_success_path_enriches_entity(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Threshold": 50, "Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_indicator.return_value = _indicator_result(
            "1.2.3.4", score=85
        )

        action = EnrichIndicator(SCRIPT_NAME)
        action.run()

        assert entity.is_enriched is True
        assert entity.is_suspicious is True  # score 85 >= threshold 50
        assert "OCTI_indicator_score" in entity.additional_properties
        assert entity.additional_properties["OCTI_indicator_score"] == 85
        assert action.result_value is True
        assert "were not found" not in action.output_message

    def test_score_below_threshold_does_not_mark_suspicious(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Threshold": 90, "Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_indicator.return_value = _indicator_result(
            "1.2.3.4", score=85
        )

        action = EnrichIndicator(SCRIPT_NAME)
        action.run()

        assert entity.is_suspicious is False

    def test_not_found_sets_false_result(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Threshold": 50, "Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_indicator.return_value = _indicator_result(found=False)

        action = EnrichIndicator(SCRIPT_NAME)
        action.run()

        assert action.result_value is False
        assert "were not found" in action.output_message
        assert entity.is_enriched is False
        entity_result = next(r for r in action.json_results if r["Entity"] == "1.2.3.4")
        assert "was not found" in entity_result["EntityResult"]["execution_status"]

    def test_partial_failure_reports_failed_entity(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Threshold": 50, "Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_indicator.side_effect = OpenCTIClientError(
            "connection refused"
        )

        action = EnrichIndicator(SCRIPT_NAME)
        action.run()

        assert action.result_value is False
        assert "wasn't able to enrich" in action.output_message
        entity_result = next(r for r in action.json_results if r["Entity"] == "1.2.3.4")
        assert "Failed to enrich" in entity_result["EntityResult"]["execution_status"]

    def test_unexpected_exception_is_reported_as_failed(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Threshold": 50, "Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_indicator.side_effect = RuntimeError("boom")

        action = EnrichIndicator(SCRIPT_NAME)
        action.run()

        assert action.result_value is False
        assert "wasn't able to enrich" in action.output_message
        entity_result = next(r for r in action.json_results if r["Entity"] == "1.2.3.4")
        assert entity_result["EntityResult"]["execution_status"] == "boom"

    def test_create_insight_is_called_when_enabled(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Create Insight": True}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_indicator.return_value = _indicator_result(
            "1.2.3.4", score=60
        )

        action = EnrichIndicator(SCRIPT_NAME)
        action.run()

        mock_soar_enrich_action.add_entity_insight.assert_called_once()
        args = mock_soar_enrich_action.add_entity_insight.call_args[0]
        assert args[0] is entity
        assert "OpenCTI Score" in args[1]

    def test_create_insight_is_not_called_when_disabled(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_indicator.return_value = _indicator_result(
            "1.2.3.4", score=60
        )

        action = EnrichIndicator(SCRIPT_NAME)
        action.run()

        mock_soar_enrich_action.add_entity_insight.assert_not_called()

    def test_kill_chain_in_enrichment_data(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_indicator.return_value = _indicator_result(
            "1.2.3.4",
            kill_chain_phases=[
                {"kill_chain_name": "mitre-attack", "phase_name": "initial-access"}
            ],
        )

        action = EnrichIndicator(SCRIPT_NAME)
        action.run()

        assert "OCTI_indicator_kill_chain" in entity.additional_properties
        assert (
            "initial-access"
            in entity.additional_properties["OCTI_indicator_kill_chain"]
        )

    def test_relations_add_data_table(self, mock_soar_enrich_action, mock_api_client):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        relationships = [
            {
                "relation_type": "indicates",
                "related_entity_type": "Malware",
                "related_entity_name": "Cobalt Strike",
            }
        ]
        mock_api_client.enrich_indicator.return_value = _indicator_result(
            "1.2.3.4", relationships=relationships
        )

        action = EnrichIndicator(SCRIPT_NAME)
        action.run()

        mock_soar_enrich_action.result.add_data_table.assert_called_once()
        title = mock_soar_enrich_action.result.add_data_table.call_args.kwargs["title"]
        assert "Indicator Relations" in title

    def test_multiple_entities_mixed_results(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity_found = _make_entity("1.2.3.4", "ADDRESS")
        entity_missing = _make_entity("safe.example.com", "DOMAIN")
        mock_soar_enrich_action.parameters = {"Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity_found, entity_missing]

        def side_effect(entity):
            if entity.original_identifier == "1.2.3.4":
                return _indicator_result("1.2.3.4", score=50)
            return None

        mock_api_client.enrich_indicator.side_effect = side_effect

        action = EnrichIndicator(SCRIPT_NAME)
        action.run()

        assert entity_found.is_enriched is True
        assert entity_missing.is_enriched is False
        assert "were not found" in action.output_message
        entity_result = next(
            r for r in action.json_results if r["Entity"] == "safe.example.com"
        )
        assert "was not found" in entity_result["EntityResult"]["execution_status"]
