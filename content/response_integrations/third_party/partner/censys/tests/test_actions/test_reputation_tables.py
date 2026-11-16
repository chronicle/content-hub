from __future__ import annotations

from unittest.mock import Mock

from TIPCommon.types import SingleJson

from censys.core.constants import (
    REPUTATION_CLASS_PROBABILITIES_TABLE_NAME,
    REPUTATION_EVIDENCE_TABLE_NAME,
    REPUTATION_SUMMARY_TABLE_NAME,
)
from censys.core.reputation import ReputationTables

SAMPLE_REPUTATION: SingleJson = {
    "label": "SUSPICIOUS",
    "score": 0.666,
    "score_suppressed": False,
    "class_probabilities": [
        {"label": "BENIGN", "probability": 0.1},
        {"label": "SUSPICIOUS", "probability": 0.8},
    ],
    "evidence": [
        {
            "feature": {
                "id": "max_port",
                "name": "Max Port",
                "value": "49093",
                "contribution": 0.0793,
                "category": "service_surface",
            }
        }
    ],
}


class TestReputationTables:
    """Unit tests for the ReputationTables accumulator shared by Enrich Host -
    Get Host API and Enrich Host - Get Host Enrichment API, isolated from the
    full SiemplifyAction/entity-loop machinery so the "one combined table per
    run, no-op when empty" contract is directly verifiable."""

    def test_accumulates_rows_across_multiple_ips(self) -> None:
        tables = ReputationTables()

        tables.add("1.1.1.1", SAMPLE_REPUTATION)
        tables.add("8.8.8.8", {**SAMPLE_REPUTATION, "label": "BENIGN"})

        assert len(tables.summary_rows) == 2
        assert {row["IP"] for row in tables.summary_rows} == {"1.1.1.1", "8.8.8.8"}
        # One combined table, one row per IP - not per-IP separate tables.
        assert len(tables.class_probability_rows) == 4  # 2 labels x 2 IPs
        assert len(tables.evidence_rows) == 2  # 1 evidence entry x 2 IPs

    def test_ignores_ips_with_no_reputation_data(self) -> None:
        tables = ReputationTables()

        tables.add("1.1.1.1", SAMPLE_REPUTATION)
        tables.add("8.8.8.8", None)  # No reputation data for this IP.

        assert len(tables.summary_rows) == 1
        assert tables.summary_rows[0]["IP"] == "1.1.1.1"

    def test_adds_all_three_tables_when_rows_present(self) -> None:
        mock_siemplify = Mock()
        tables = ReputationTables(
            summary_rows=[{"IP": "1.1.1.1", "Label": "SUSPICIOUS"}],
            class_probability_rows=[{"IP": "1.1.1.1", "Label": "BENIGN"}],
            evidence_rows=[{"IP": "1.1.1.1", "Feature": "Max Port"}],
        )

        tables.add_to_case_wall(mock_siemplify)

        assert mock_siemplify.result.add_data_table.call_count == 3
        table_names = [call.args[0] for call in mock_siemplify.result.add_data_table.call_args_list]
        assert REPUTATION_SUMMARY_TABLE_NAME in table_names
        assert REPUTATION_CLASS_PROBABILITIES_TABLE_NAME in table_names
        assert REPUTATION_EVIDENCE_TABLE_NAME in table_names

    def test_no_tables_added_when_no_rows(self) -> None:
        # No entity in the run had reputation data - must not add empty tables.
        mock_siemplify = Mock()

        ReputationTables().add_to_case_wall(mock_siemplify)

        mock_siemplify.result.add_data_table.assert_not_called()

    def test_partial_data_only_adds_non_empty_tables(self) -> None:
        # A host may have a reputation label/score but no evidence entries.
        mock_siemplify = Mock()
        tables = ReputationTables(
            summary_rows=[{"IP": "1.1.1.1", "Label": "BENIGN"}],
        )

        tables.add_to_case_wall(mock_siemplify)

        mock_siemplify.result.add_data_table.assert_called_once()
        assert mock_siemplify.result.add_data_table.call_args.args[0] == REPUTATION_SUMMARY_TABLE_NAME
