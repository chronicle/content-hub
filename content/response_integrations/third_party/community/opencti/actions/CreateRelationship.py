from __future__ import annotations

from pydantic import AwareDatetime, Field, field_validator

from ..core.base_action import BaseAction
from ..core.base_action_parameters import BaseActionParameters
from ..core.datamodels.relationship import Relationship
from ..core.utils import convert_date_format

SCRIPT_NAME = "Create Relationship"


class CreateRelationshipParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    relationship_type: str = Field(
        description="Specify relationship type",
        default="related-to",
    )
    source_entity_id: str = Field(
        description="Specify source entity ID",
    )
    target_entity_id: str = Field(
        description="Specify target entity ID",
    )
    description: str | None = Field(
        description="Specify relationship description",
        default=None,
    )
    first_seen: AwareDatetime | None = Field(
        description="Specify first seen date (ISO 8601 format)",
        default=None,
    )
    last_seen: AwareDatetime | None = Field(
        description="Specify last seen date (ISO 8601 format)",
        default=None,
    )
    marking: str | None = Field(
        description="Specify marking for the relationship",
        default=None,
    )

    @field_validator("first_seen", "last_seen", mode="before")
    @classmethod
    def _parse_datetimes(cls, value: str | None) -> str | None:
        """Normalize supported datetime input into ISO 8601 UTC format.

        Args:
            value: Raw datetime string from the action form.

        Returns:
            The normalized datetime string, or the original value if empty/non-string.
        """
        if not isinstance(value, str) or not value:
            return value

        return convert_date_format(value)


class CreateRelationship(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateRelationshipParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateRelationshipParameters(  # type: ignore[assignment]
            relationship_type=raw_params.get("Relationship Type"),
            source_entity_id=raw_params.get("Source Entity Id"),
            target_entity_id=raw_params.get("Target Entity Id"),
            description=raw_params.get("Description"),
            first_seen=raw_params.get("First Seen"),
            last_seen=raw_params.get("Last Seen"),
            marking=raw_params.get("Marking"),
        )

    def _perform_action(self, _=None) -> None:
        """Create a Relationship in OpenCTI between the provided source and target entities.
        On success it returns the created relationship details in output fields;
        on failure an exception propagates and the framework marks the action as failed.
        """
        relationship = Relationship(
            relationship_type=self.params.relationship_type,
            source_ref=self.params.source_entity_id,
            target_ref=self.params.target_entity_id,
            description=self.params.description,
            first_seen=self.params.first_seen,
            last_seen=self.params.last_seen,
            markings=[self.params.marking] if self.params.marking else None,
        )
        result = self.api_client.create_relationship(relationship)

        self.output_message = f"Relationship successfully created with ID {result.id}"

        self.json_results = result.json() or {}


def main() -> None:
    """Action entry point."""
    CreateRelationship(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
