from abc import ABC
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class BaseJSONResult(BaseModel, ABC):
    model_config = ConfigDict(
        # Ignore extra fields that are not defined in the model without raising a validation error
        extra="ignore",
        # Make the model immutable to prevent accidental modifications
        frozen=True,
        # Validate default values to ensure they conform to the field types and constraints
        validate_default=True,
    )

    def json(self) -> dict[str, Any]:
        """
        Serialize the model to a JSON-compatible dictionary.
        """
        return self.model_dump(mode="json")


class BaseObjectJSONResult(BaseJSONResult):
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
    entity_type: Literal["Incident"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Incident"],
    )


class IncidentResponseJSONResult(BaseObjectJSONResult):
    entity_type: Literal["Case-Incident"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Case-Incident"],
    )


class RequestForInformationJSONResult(BaseObjectJSONResult):
    entity_type: Literal["Case-Rfi"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Case-Rfi"],
    )


class RequestForTakedownJSONResult(BaseObjectJSONResult):
    entity_type: Literal["Case-Rft"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Case-Rft"],
    )


class ObservableJSONResult(BaseObjectJSONResult):
    # Entity type can vary for observables depending on API projection.
    entity_type: str = Field(
        description="The type of the observable object on OpenCTI",
        examples=["Stix-Cyber-Observable"],
    )


class ReportJSONResult(BaseObjectJSONResult):
    entity_type: Literal["Report"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Report"],
    )

class AttackPatternJSONResult(BaseObjectJSONResult):
    entity_type: Literal["Attack-Pattern"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Attack-Pattern"],
    )

class AddObjectToContainerJSONResult(BaseJSONResult):
    """Result for `AddObjectToContainer` action.

    pycti's `add_stix_object_or_stix_relationship` methods return `True` on success and
    `False` on failure — it never returns the container payload.
    This model builds a result based on input paramters so the action's output
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
