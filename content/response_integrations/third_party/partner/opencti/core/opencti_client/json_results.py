from __future__ import annotations

from abc import ABC
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BaseJSONResult(BaseModel, ABC):
    """Base class for action JSON result models."""

    model_config = ConfigDict(
        # Ignore extra fields that are not defined in the model without raising a validation error
        extra="ignore",
        # Make the model immutable to prevent accidental modifications
        frozen=True,
        # Validate default values to ensure they conform to the field types and constraints
        validate_default=True,
    )

    def json(self) -> dict[str, Any]:
        """Serialize the model to a JSON-compatible dictionary."""
        return self.model_dump(mode="json")


class BaseObjectJSONResult(BaseJSONResult):
    """Shared JSON result fields for OpenCTI object creation actions."""

    id: str = Field(
        description="The unique identifier of the object on OpenCTI",
        examples=["20f7568f-e6f4-4bcc-8cc8-d6d5ba366622"],
    )
    standard_id: str = Field(
        description="The deterministic STIX 2.1 ID of the object on OpenCTI",
        examples=["incident--79249898-aaf5-5843-8080-1cab8511771d"],
    )
    entity_type: str = Field(
        description="The type of the object on OpenCTI",
        examples=["Incident"],
    )
    parent_types: list[str] = Field(
        description="The types the object inherits from on OpenCTI",
        examples=[
            [
                "Basic-Object",
                "Stix-Object",
                "Stix-Core-Object",
            ]
        ],
    )
    created_by_id: str | None = Field(
        validation_alias="createdById",
        description="The identifier of the user who created the object on OpenCTI",
        examples=["bd0f37dc-27a8-4ead-aa7d-1d63082a9318"],
    )


class IncidentJSONResult(BaseObjectJSONResult):
    """Result of `CreateIncident` action."""

    entity_type: Literal["Incident"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Incident"],
    )


class IncidentResponseJSONResult(BaseObjectJSONResult):
    """Result of `CreateIncidentResponse` action."""

    entity_type: Literal["Case-Incident"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Case-Incident"],
    )


class RequestForInformationJSONResult(BaseObjectJSONResult):
    """Result of `CreateRequestForInformation` action."""

    entity_type: Literal["Case-Rfi"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Case-Rfi"],
    )


class RequestForTakedownJSONResult(BaseObjectJSONResult):
    """Result of `CreateRequestForTakedown` action."""

    entity_type: Literal["Case-Rft"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Case-Rft"],
    )


class ObservableJSONResult(BaseObjectJSONResult):
    # Entity type can vary for observables depending on API projection.
    """Result of `CreateObservable` action."""
    entity_type: str = Field(
        description="The type of the observable object on OpenCTI",
        examples=["Stix-Cyber-Observable"],
    )


class ReportJSONResult(BaseObjectJSONResult):
    """Result of `CreateReport` action."""

    entity_type: Literal["Report"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Report"],
    )


class GroupingJSONResult(BaseObjectJSONResult):
    """Result of `CreateGrouping` action."""

    entity_type: Literal["Grouping"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Grouping"],
    )


class RelationshipJSONResult(BaseObjectJSONResult):
    """Result of `CreateRelationship` action."""

    entity_type: str = Field(
        description="The type of the object on OpenCTI",
        examples=["related-to", "stix-core-relationship"],
    )


class VulnerabilityJSONResult(BaseObjectJSONResult):
    """Result of `CreateVulnerability` action."""

    entity_type: Literal["Vulnerability"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Vulnerability"],
    )


class MalwareJSONResult(BaseObjectJSONResult):
    """Result of `CreateMalware` action."""

    entity_type: Literal["Malware"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Malware"],
    )


class ThreatActorGroupJSONResult(BaseObjectJSONResult):
    """Result of `CreateThreatActorGroup` action."""

    entity_type: Literal["Threat-Actor-Group"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Threat-Actor-Group"],
    )


class IntrusionSetJSONResult(BaseObjectJSONResult):
    """Result of `CreateIntrusionSet` action."""

    entity_type: Literal["Intrusion-Set"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Intrusion-Set"],
    )


class CampaignJSONResult(BaseObjectJSONResult):
    """Result of `CreateCampaign` action."""

    entity_type: Literal["Campaign"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Campaign"],
    )


class ToolJSONResult(BaseObjectJSONResult):
    """Result of `CreateTool` action."""

    entity_type: Literal["Tool"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Tool"],
    )


class AttackPatternJSONResult(BaseObjectJSONResult):
    """Result of `CreateAttackPattern` action."""

    entity_type: Literal["Attack-Pattern"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Attack-Pattern"],
    )


class IndicatorJSONResult(BaseObjectJSONResult):
    """Result of `CreateIndicator` action."""

    entity_type: Literal["Indicator"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Indicator"],
    )


class SightingJSONResult(BaseObjectJSONResult):
    """Result of `CreateSighting` action."""

    entity_type: Literal["Sighting", "stix-sighting-relationship"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Sighting", "stix-sighting-relationship"],
    )


class AddObjectToContainerJSONResult(BaseJSONResult):
    """Result of `AddObjectToContainer` action.

    pycti's `add_stix_object_or_stix_relationship` methods return `True` on success and
    `False` on failure — it never returns the container payload.
    This model builds a result based on input parameters so the action's output
    can be re-used in subsequent actions (typically in a playbook).
    """

    container_entity_type: Literal[
        "Report",
        "Case-Incident",
        "Case-Rfi",
        "Case-Rft",
        "Grouping",
    ] = Field(
        description="Normalized container type used for the add operation.",
        examples=["Report", "Case-Incident", "Case-Rfi", "Case-Rft", "Grouping"],
    )
    container_id: str = Field(
        description="Identifier of the target container used for the add operation.",
    )
    object_id: str = Field(
        description="Identifier of the object that was added to the container.",
    )
