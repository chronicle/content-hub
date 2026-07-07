from __future__ import annotations

from unittest.mock import MagicMock

from ...actions.EnrichObservable import (
    SCRIPT_NAME,
    EnrichObservable,
    EnrichObservableParameters,
)
from ...core.opencti_client.client import OpenCTIClientError
from ...core.opencti_client.enrich_results import ObservableEnrichmentResult


def _make_entity(identifier: str, entity_type: str = "ADDRESS") -> MagicMock:
    entity = MagicMock()
    entity.entity_type = entity_type
    entity.identifier = identifier
    entity.original_identifier = identifier
    entity.additional_properties = {}
    entity.is_enriched = False
    entity.is_suspicious = False
    return entity


def _observable_result(
    identifier: str = "1.2.3.4",
    score: int = 75,
    found: bool = True,
    labels: list[str] | None = None,
    relationships: list[dict] | None = None,
) -> ObservableEnrichmentResult | None:
    _ = identifier  # observable's value is not stored in the result object, only the ID and type are.

    if not found:
        return None
    return ObservableEnrichmentResult(
        id="obs-id-1",
        entity_type="IPv4-Addr",
        x_opencti_score=score,
        labelObject=labels or ["malicious"],
        link="https://opencti.example.com/dashboard/id/obs-id-1",
        relationships=relationships or [],
    )


class TestEnrichObservableParameters:
    def test_defaults(self):
        params = EnrichObservableParameters()
        assert params.threshold == 50
        assert params.create_insight is True

    def test_custom_values(self):
        params = EnrichObservableParameters(threshold=80, create_insight=False)
        assert params.threshold == 80
        assert params.create_insight is False


class TestEnrichObservableAction:
    def test_validate_params_reads_threshold_and_insight(self, mock_soar_enrich_action):
        mock_soar_enrich_action.parameters = {"Threshold": 75, "Create Insight": False}
        action = EnrichObservable(SCRIPT_NAME)
        action._validate_params()
        assert action.params.threshold == 75
        assert action.params.create_insight is False

    def test_unsupported_entity_types_are_skipped(
        self, mock_soar_enrich_action, mock_api_client
    ):
        """CVE and THREATACTOR entities should not reach the API call."""
        mock_soar_enrich_action.parameters = {}
        mock_soar_enrich_action.target_entities = [
            _make_entity("CVE-2024-1234", "CVE"),
            _make_entity("EvilGroup", "THREATACTOR"),
        ]
        action = EnrichObservable(SCRIPT_NAME)
        action.run()
        mock_api_client.enrich_observable.assert_not_called()
        assert action.result_value is False
        assert "supported entity types" in action.output_message

    def test_success_path_enriches_entity(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Threshold": 50, "Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_observable.return_value = _observable_result(
            "1.2.3.4", score=75
        )

        action = EnrichObservable(SCRIPT_NAME)
        action.run()

        assert entity.is_enriched is True
        assert entity.is_suspicious is True  # score 75 >= threshold 50
        assert "OCTI_observable_score" in entity.additional_properties
        assert entity.additional_properties["OCTI_observable_score"] == 75
        assert action.result_value is True
        assert "were not found" not in action.output_message

    def test_score_below_threshold_does_not_mark_suspicious(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Threshold": 80, "Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_observable.return_value = _observable_result(
            "1.2.3.4", score=75
        )

        action = EnrichObservable(SCRIPT_NAME)
        action.run()

        assert entity.is_suspicious is False

    def test_not_found_sets_false_result(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Threshold": 50, "Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_observable.return_value = _observable_result(found=False)

        action = EnrichObservable(SCRIPT_NAME)
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
        mock_api_client.enrich_observable.side_effect = OpenCTIClientError("API down")

        action = EnrichObservable(SCRIPT_NAME)
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
        mock_api_client.enrich_observable.side_effect = RuntimeError("boom")

        action = EnrichObservable(SCRIPT_NAME)
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
        mock_api_client.enrich_observable.return_value = _observable_result(
            "1.2.3.4", score=60
        )

        action = EnrichObservable(SCRIPT_NAME)
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
        mock_api_client.enrich_observable.return_value = _observable_result(
            "1.2.3.4", score=60
        )

        action = EnrichObservable(SCRIPT_NAME)
        action.run()

        mock_soar_enrich_action.add_entity_insight.assert_not_called()

    def test_relations_add_data_table(self, mock_soar_enrich_action, mock_api_client):
        entity = _make_entity("evil.com", "DOMAIN")
        mock_soar_enrich_action.parameters = {"Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        relationships = [
            {
                "relation_type": "related-to",
                "related_entity_type": "Malware",
                "related_entity_name": "Cobalt Strike",
            }
        ]
        mock_api_client.enrich_observable.return_value = _observable_result(
            "evil.com", relationships=relationships
        )

        action = EnrichObservable(SCRIPT_NAME)
        action.run()

        mock_soar_enrich_action.result.add_data_table.assert_called_once()
        title = mock_soar_enrich_action.result.add_data_table.call_args.kwargs["title"]
        assert "Observable Relations" in title

    def test_link_adds_entity_link(self, mock_soar_enrich_action, mock_api_client):
        entity = _make_entity("1.2.3.4", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity]
        mock_api_client.enrich_observable.return_value = _observable_result(
            "1.2.3.4", score=60
        )

        action = EnrichObservable(SCRIPT_NAME)
        action.run()

        mock_soar_enrich_action.result.add_entity_link.assert_called_once()

    def test_multiple_entities_mixed_results(
        self, mock_soar_enrich_action, mock_api_client
    ):
        entity_found = _make_entity("1.2.3.4", "ADDRESS")
        entity_missing = _make_entity("9.9.9.9", "ADDRESS")
        mock_soar_enrich_action.parameters = {"Create Insight": False}
        mock_soar_enrich_action.target_entities = [entity_found, entity_missing]

        def side_effect(entity):
            if entity.original_identifier == "1.2.3.4":
                return _observable_result("1.2.3.4", score=50)
            return None

        mock_api_client.enrich_observable.side_effect = side_effect

        action = EnrichObservable(SCRIPT_NAME)
        action.run()

        assert entity_found.is_enriched is True
        assert entity_missing.is_enriched is False
        assert "were not found" in action.output_message
        entity_result = next(r for r in action.json_results if r["Entity"] == "9.9.9.9")
        assert "was not found" in entity_result["EntityResult"]["execution_status"]
