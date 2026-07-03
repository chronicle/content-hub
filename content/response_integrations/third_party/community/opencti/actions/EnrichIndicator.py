from __future__ import annotations

from typing import TYPE_CHECKING

from core.base_action import BaseEnrichAction, EntityNotFoundError
from core.base_action_parameters import BaseActionParameters
from core.opencti_client.client import OpenCTIClientError
from core.utils import score_to_color
from pydantic import Field
from TIPCommon.base.action import EntityTypesEnum
from TIPCommon.base.action.base_enrich_action import EnrichActionError
from TIPCommon.transformation import construct_csv

if TYPE_CHECKING:
    from core.opencti_client.enrich_results import IndicatorEnrichmentResult
    from TIPCommon.types import Entity

SCRIPT_NAME = "Enrich Indicator"

SUPPORTED_ENTITY_TYPES = [
    EntityTypesEnum.ADDRESS,
    EntityTypesEnum.FILE_HASH,
    EntityTypesEnum.URL,
    EntityTypesEnum.HOST_NAME,
    EntityTypesEnum.DOMAIN,
]


class EnrichIndicatorParameters(BaseActionParameters):
    """Represent the EnrichIndicatorParameters model."""

    threshold: int = Field(
        description="The minimum OpenCTI score required to mark a Google SecOps entity as suspicious.",
        default=50,
    )
    create_insight: bool = Field(
        description="If enabled, creates an insight containing retrieved indicator data and its relationships.",
        default=True,
    )


class EnrichIndicator(BaseEnrichAction):
    """Full enrichment of an Indicator (SDO) in OpenCTI."""

    @property
    def params(self) -> EnrichIndicatorParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        self._params = EnrichIndicatorParameters(  # type: ignore[assignment]
            threshold=self.soar_action.parameters.get("Threshold"),
            create_insight=self.soar_action.parameters.get("Create Insight"),
        )

    def _get_entity_types(self) -> list[EntityTypesEnum]:
        """Return the entity types supported by this enrichment action.

        Returns:
            list[EntityTypesEnum]: Entity types eligible for OpenCTI indicator enrichment.
        """
        return SUPPORTED_ENTITY_TYPES

    def _perform_enrich_action(self, current_entity: Entity) -> None:  # type: ignore[type-var]
        """Enrich one entity with indicator context fetched from OpenCTI.

        This method runs once per entity; the base enrichment flow calls it in a
        loop from `_perform_action` for all eligible target entities.

        On success, the method stores entity results, updates enrichment fields,
        and optionally adds links, relationship tables, and an insight.
        If enrichment cannot be completed,
        an exception propagates and the framework marks this entity enrichment as failed.

        Args:
            current_entity: The Google SecOps entity currently being enriched.
        """
        identifier = current_entity.original_identifier

        try:
            enrichment = self.api_client.enrich_indicator(current_entity)
            if enrichment is None:
                raise EntityNotFoundError(
                    f"Indicator '{identifier}' was not found in OpenCTI"
                )
        except OpenCTIClientError as e:
            raise EnrichActionError(
                f"Failed to enrich indicator '{identifier}': {str(e)}"
            ) from e

        self.entity_results = enrichment.json()

        if enrichment.score is not None and enrichment.score >= self.params.threshold:
            current_entity.is_suspicious = True

        # self.enrichment_data is used in the base class to
        # update the entity's additional_properties
        self.enrichment_data = self._get_enrichment_data(enrichment)

        if enrichment.link:
            self._create_entity_link(current_entity, enrichment)
        if enrichment.relationships:
            self._create_relationships_table(current_entity, enrichment)

        if self.params.create_insight:
            self._create_entity_insight(current_entity, enrichment)

    def _get_enrichment_data(
        self, enrichment: IndicatorEnrichmentResult
    ) -> dict[str, str | int]:
        """Flat dict injected into current_entity.additional_properties."""
        prefix = "OCTI"

        data: dict[str, str | int] = {}
        if enrichment.score is not None:
            data[f"{prefix}_indicator_score"] = enrichment.score
        if enrichment.confidence is not None:
            data[f"{prefix}_indicator_confidence"] = enrichment.confidence
        if enrichment.valid_from:
            data[f"{prefix}_indicator_valid_from"] = enrichment.valid_from.isoformat()
        if enrichment.valid_until:
            data[f"{prefix}_indicator_valid_until"] = enrichment.valid_until.isoformat()
        if enrichment.pattern:
            data[f"{prefix}_indicator_pattern"] = enrichment.pattern
        if enrichment.labels:
            data[f"{prefix}_indicator_labels"] = ", ".join(enrichment.labels)
        if enrichment.created_by:
            data[f"{prefix}_indicator_created_by"] = enrichment.created_by
        if enrichment.kill_chain_phases:
            phases = [
                f"{kill_chain.get('kill_chain_name', '')}::{kill_chain.get('phase_name', '')}"
                for kill_chain in enrichment.kill_chain_phases
            ]
            data[f"{prefix}_indicator_kill_chain"] = ", ".join(phases)

        return data

    def _create_entity_link(
        self, current_entity: Entity, enrichment: IndicatorEnrichmentResult  # type: ignore[type-var]
    ) -> None:
        """Create a link to the indicator in OpenCTI."""
        self.soar_action.result.add_entity_link(
            current_entity.identifier, enrichment.link
        )

    def _create_relationships_table(
        self, current_entity: Entity, enrichment: IndicatorEnrichmentResult  # type: ignore[type-var]
    ) -> None:
        """Create a table of indicator relationships for the insight."""
        table: list[dict] = []
        for relationship in enrichment.relationships:
            table.append(
                {
                    "Relationship Type": relationship.get("relationship_type", ""),
                    "Related Entity Type": relationship.get("related_entity_type", ""),
                    "Related Entity Name": relationship.get("related_entity_name", ""),
                }
            )

        self.soar_action.result.add_data_table(
            title=f"Indicator Relationships: {current_entity.identifier}",
            data_table=construct_csv(table),
        )

    def _create_entity_insight(
        self, current_entity: Entity, enrichment: IndicatorEnrichmentResult  # type: ignore[type-var]
    ) -> None:
        """Create a rich HTML insight for the enriched entity.

        Args:
            current_entity: Enriched entity to attach the insight to.
            enrichment: Normalized indicator enrichment payload from OpenCTI.
        """
        if self.params.create_insight:
            html_parts: list[str] = []

            score = enrichment.score or 0
            html_parts.append(f"""
            <h3>
            OpenCTI Score: <span style="color:{score_to_color(score)}"><strong>{score}</strong>/100</span>
            </h3>
            <strong>Name:</strong> {enrichment.name or 'N/A'}<br>
            """)
            if enrichment.confidence is not None:
                html_parts.append(
                    f"<strong>Confidence:</strong> {enrichment.confidence}<br>"
                )
            if enrichment.valid_from:
                html_parts.append(
                    f"<strong>Valid from:</strong> {enrichment.valid_from.isoformat()}<br>"
                )
            if enrichment.valid_until:
                html_parts.append(
                    f"<strong>Valid until:</strong> {enrichment.valid_until.isoformat()}<br>"
                )
            if enrichment.pattern:
                html_parts.append(
                    f"<strong>Pattern:</strong> <code>{enrichment.pattern}</code><br>"
                )
            if enrichment.labels:
                html_parts.append(
                    f"<strong>Labels:</strong> {', '.join(enrichment.labels)}<br>"
                )
            if enrichment.created_by:
                html_parts.append(
                    f"<strong>Created by:</strong> {enrichment.created_by}<br>"
                )
            if enrichment.kill_chain_phases:
                phases = [
                    f"{kc.get('kill_chain_name', '')} \u2192 {kc.get('phase_name', '')}"
                    for kc in enrichment.kill_chain_phases
                ]
                html_parts.append(
                    f"<strong>Kill Chain:</strong> {', '.join(phases)}<br>"
                )
            if enrichment.link:
                html_parts.append(
                    f'<strong>Source:</strong> <a href="{enrichment.link}" target="_blank">{enrichment.link}</a><br>'
                )
            if enrichment.relationships:
                relationships_by_type: dict[str, list[dict]] = {}
                for relationship in enrichment.relationships:
                    relationship_type = relationship.get("relationship_type", "unknown")
                    relationships_by_type.setdefault(relationship_type, [])
                    relationships_by_type[relationship_type].append(relationship)

                for relationship_type, relationships in relationships_by_type.items():
                    html_parts.append(
                        f"<br><p><strong>{relationship_type} ({len(relationships)})</strong></p>"
                    )
                    for relationship in relationships:
                        entity_name = relationship.get("related_entity_name", "?")
                        entity_type = relationship.get("related_entity_type", "")
                        html_parts.append(
                            f"<p><strong>{entity_name}</strong> — {entity_type}</p>"
                        )
                html_parts.append("<p>&nbsp;</p>")

            insight_html = "".join(html_parts)

            self.soar_action.add_entity_insight(
                current_entity,
                insight_html,
                triggered_by=self.INTEGRATION_IDENTIFIER,
            )


def main() -> None:
    """Action entry point."""
    EnrichIndicator(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
