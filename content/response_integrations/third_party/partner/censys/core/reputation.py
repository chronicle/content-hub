from __future__ import annotations

import dataclasses
import json
from typing import TYPE_CHECKING

from soar_sdk.SiemplifyUtils import construct_csv
from TIPCommon.types import SingleJson

from .constants import (
    DEFAULT_VALUE_NA,
    ENRICHMENT_PREFIX,
    REPUTATION_CLASS_PROBABILITIES_TABLE_NAME,
    REPUTATION_DISPLAY_SCALE_FACTOR,
    REPUTATION_EVIDENCE_TABLE_NAME,
    REPUTATION_MAX_EVIDENCE_RECORDS,
    REPUTATION_SUMMARY_TABLE_NAME,
)

if TYPE_CHECKING:
    from soar_sdk.SiemplifyAction import SiemplifyAction


class ReputationExtractor:
    """
    Shared helper for extracting Censys reputation data.

    Used by both HostDatamodel (Get Host API) and HostEnrichmentDatamodel
    (Get Host Enrichment API) since both endpoints return an identical
    `reputation` object shape at result.resource.reputation.

    Censys returns score, class_probabilities[].probability, and
    evidence[].feature.contribution as 0-1 fractions. The Censys UI displays
    these multiplied by 100 (e.g. raw score 0.666 -> displayed 66.6), so all
    three are scaled the same way here for display fields.
    """

    @staticmethod
    def _scale(value: float | int | str | None) -> float | None:
        """
        Scale a 0-1 fraction to a 0-100 display value.

        Returns None (rather than raising) for non-numeric or missing input,
        since Censys may omit a value (e.g. a class_probabilities entry with
        no "probability" key when its probability is negligible).
        """
        if value is None:
            return None
        try:
            return round(float(value) * REPUTATION_DISPLAY_SCALE_FACTOR, 2)
        except (TypeError, ValueError):
            return None

    @classmethod
    def get_entity_enrichment_fields(cls, reputation: SingleJson | None) -> SingleJson:
        """
        Build reputation entity properties.

        Args:
            reputation: The raw `reputation` object from result.resource.reputation.
                May be None/{} when the host has no reputation data.

        Returns:
            Dict of Censys_reputation_* entity properties. Existing
            Censys_reputation_score (raw) and Censys_reputation_score_level
            are intentionally left for callers to set separately so their
            values/semantics stay unchanged for backward compatibility.
        """
        reputation = reputation or {}
        if not reputation:
            return {}

        class_probabilities = cls._scaled_class_probabilities(reputation)
        evidence = cls._compact_evidence_for_entity(reputation)

        fields = {
            f"{ENRICHMENT_PREFIX}reputation_label": reputation.get("label"),
            f"{ENRICHMENT_PREFIX}reputation_score_percent": cls._scale(reputation.get("score")),
            f"{ENRICHMENT_PREFIX}reputation_score_suppressed": reputation.get("score_suppressed"),
            f"{ENRICHMENT_PREFIX}reputation_class_probabilities": (
                json.dumps(class_probabilities) if class_probabilities else None
            ),
            f"{ENRICHMENT_PREFIX}reputation_evidence": (json.dumps(evidence) if evidence else None),
        }

        return {k: v for k, v in fields.items() if v is not None}

    @classmethod
    def _compact_evidence_for_entity(cls, reputation: SingleJson) -> list[SingleJson]:
        """
        Compact evidence shape for the entity JSON property only.

        SecOps entity property values have a limited display/storage width,
        so this drops feature_id (redundant with feature_name - the
        human-readable name a SOC analyst reads) to keep the property small.
        feature_id remains available in full via add_result_json (the raw
        JSON case wall result) and the Evidence data table for anyone who
        needs it. Table rows use the fuller _scaled_evidence() shape instead.
        """
        return [
            {
                "feature": entry.get("feature_name") or entry.get("feature_id"),
                "value": entry.get("value"),
                "contribution": entry.get("contribution"),
                "category": entry.get("category"),
            }
            for entry in cls._scaled_evidence(reputation)
        ]

    @classmethod
    def _scaled_class_probabilities(cls, reputation: SingleJson) -> list[SingleJson]:
        """Return class_probabilities with probability scaled 0-100."""
        result: list[SingleJson] = []
        for entry in reputation.get("class_probabilities") or []:
            if not isinstance(entry, dict):
                continue
            result.append({
                "label": entry.get("label"),
                "probability": cls._scale(entry.get("probability")),
            })
        return result

    @classmethod
    def _scaled_evidence(cls, reputation: SingleJson) -> list[SingleJson]:
        """
        Return top evidence entries (by contribution, descending) with
        contribution scaled 0-100, limited to REPUTATION_MAX_EVIDENCE_RECORDS.
        """
        raw_evidence = [entry for entry in (reputation.get("evidence") or []) if isinstance(entry, dict)]

        def _contribution(entry: SingleJson) -> float:
            feature = entry.get("feature") or {}
            try:
                return float(feature.get("contribution") or 0)
            except (TypeError, ValueError):
                return 0.0

        top_evidence = sorted(raw_evidence, key=_contribution, reverse=True)[:REPUTATION_MAX_EVIDENCE_RECORDS]

        result: list[SingleJson] = []
        for entry in top_evidence:
            feature = entry.get("feature") or {}
            result.append({
                "feature_id": feature.get("id"),
                "feature_name": feature.get("name"),
                "value": feature.get("value"),
                "contribution": cls._scale(feature.get("contribution")),
                "category": feature.get("category"),
            })
        return result

    @classmethod
    def get_summary_row(cls, ip: str, reputation: SingleJson | None) -> SingleJson | None:
        """Build one row for the combined Reputation Summary table."""
        reputation = reputation or {}
        if not reputation:
            return None

        return {
            "IP": ip,
            "Label": reputation.get("label", DEFAULT_VALUE_NA),
            "Score": cls._scale(reputation.get("score")),
            "Score Suppressed": reputation.get("score_suppressed", DEFAULT_VALUE_NA),
        }

    @classmethod
    def get_class_probability_rows(cls, ip: str, reputation: SingleJson | None) -> list[SingleJson]:
        """Build rows for the combined Class Probabilities table."""
        rows: list[SingleJson] = []
        for entry in cls._scaled_class_probabilities(reputation or {}):
            rows.append({
                "IP": ip,
                "Label": entry.get("label", DEFAULT_VALUE_NA),
                "Probability (%)": entry.get("probability"),
            })
        return rows

    @classmethod
    def get_evidence_rows(cls, ip: str, reputation: SingleJson | None) -> list[SingleJson]:
        """
        Build rows for the combined Evidence table (top N by contribution).

        Note: dict key order here does NOT control the rendered column
        order - soar_sdk's construct_csv() derives table headers via
        set.union, which has non-deterministic iteration order in CPython
        (confirmed: the same input produces a different column order on
        every process run). Column naming still matches the Censys web
        UI's "Top Signals" panel ("Contribution (%)") since that part is
        under our control; actual left-to-right position is not, until
        that upstream soar_sdk bug is fixed. See
        Censys-new-support/soar_sdk_construct_csv_nondeterministic_columns_bug.md.
        """
        rows: list[SingleJson] = []
        for entry in cls._scaled_evidence(reputation or {}):
            rows.append({
                "IP": ip,
                "Feature": entry.get("feature_name") or entry.get("feature_id", DEFAULT_VALUE_NA),
                "Value": entry.get("value", DEFAULT_VALUE_NA),
                "Contribution (%)": entry.get("contribution"),
                "Category": entry.get("category", DEFAULT_VALUE_NA),
            })
        return rows


@dataclasses.dataclass(slots=True)
class ReputationTables:
    """Accumulates combined reputation table rows across all processed IPs."""

    summary_rows: list[SingleJson] = dataclasses.field(default_factory=list)
    class_probability_rows: list[SingleJson] = dataclasses.field(default_factory=list)
    evidence_rows: list[SingleJson] = dataclasses.field(default_factory=list)

    def add(self, ip: str, reputation: SingleJson | None) -> None:
        """Add this IP's reputation rows to each accumulator, if any exist."""
        summary_row = ReputationExtractor.get_summary_row(ip, reputation)
        if summary_row:
            self.summary_rows.append(summary_row)
        self.class_probability_rows.extend(ReputationExtractor.get_class_probability_rows(ip, reputation))
        self.evidence_rows.extend(ReputationExtractor.get_evidence_rows(ip, reputation))

    def add_to_case_wall(self, siemplify: SiemplifyAction) -> None:
        """Add the combined reputation data tables to the case wall.

        One row per processed IP. No-ops for any table whose row list is
        empty (e.g. when no processed host had reputation data).
        """
        tables = (
            (REPUTATION_SUMMARY_TABLE_NAME, self.summary_rows),
            (REPUTATION_CLASS_PROBABILITIES_TABLE_NAME, self.class_probability_rows),
            (REPUTATION_EVIDENCE_TABLE_NAME, self.evidence_rows),
        )
        for table_name, rows in tables:
            if rows:
                siemplify.result.add_data_table(table_name, construct_csv(rows), "Censys")
