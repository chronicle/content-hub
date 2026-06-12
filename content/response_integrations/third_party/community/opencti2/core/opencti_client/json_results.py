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

    def json(self) -> dict[str, Any]:
        """
        Serialize the model to a JSON-compatible dictionary.
        """
        return self.model_dump(mode="json")


class IncidentJSONResult(BaseJSONResult):
    entity_type: Literal["Case-Incident"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Case-Incident"],
    )


class RequestForInformationJSONResult(BaseJSONResult):
    entity_type: Literal["Case-Rfi"] = Field(
        description="The type of the object on OpenCTI",
        examples=["Case-Rfi"],
    )
