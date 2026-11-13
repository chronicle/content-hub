from __future__ import annotations

from abc import ABC
from datetime import datetime
from typing import Any

from pydantic import (
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

# Prefix applied to all keys injected into entity.additional_properties
ENRICHMENT_PREFIX = "OCTI"


class BaseEnrichmentResult(BaseModel, ABC):
    """Base class for enrichment results."""

    model_config = ConfigDict(
        # Ignore extra fields that are not defined in the model without raising a validation error
        extra="ignore",
        # Make the model immutable to prevent accidental modifications
        frozen=True,
        # Validate default values to ensure they conform to the field types and constraints
        validate_default=True,
    )

    id: str
    link: str
    labels: list[str] = Field(
        validation_alias="objectLabel",
        default_factory=list,
    )
    created_by: str | None = Field(
        validation_alias=AliasPath("createdBy", "name"),
        default=None,
    )
    relationships: list[dict] = Field(default_factory=list)

    @field_validator("labels", mode="before")
    @classmethod
    def _extract_labels_names(cls, value: Any) -> list[str]:
        """Extract labels names.

        Args:
            value: Any value.

        Returns:
            list[str]: List of label names.
        """
        if isinstance(value, list):
            return [label.get("value") for label in value if label.get("value")]
        return []

    def json(self) -> dict[str, Any]:
        """Serialize the model to a JSON-compatible dictionary."""
        return self.model_dump(mode="json")


class ObservableEnrichmentResult(BaseEnrichmentResult):
    """Full enrichment result for a StixCyberObservable (SCO)."""

    observable_type: str = Field(
        validation_alias="entity_type",
    )
    score: int | None = Field(
        validation_alias="x_opencti_score",
        default=None,
    )
    description: str | None = Field(
        validation_alias="x_opencti_description",
        default=None,
    )


class IndicatorEnrichmentResult(BaseEnrichmentResult):
    """Full enrichment result for an Indicator (SDO)."""

    pattern: str
    name: str | None = None
    score: int | None = Field(
        validation_alias="x_opencti_score",
        default=None,
    )
    confidence: int | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    kill_chain_phases: list[dict] = Field(
        validation_alias="killChainPhases",
        default_factory=list,
    )
