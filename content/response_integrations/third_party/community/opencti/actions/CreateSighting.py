from __future__ import annotations

from pydantic import AwareDatetime, Field, field_validator

from ..core.base_action import BaseAction
from ..core.base_action_parameters import BaseActionParameters
from ..core.datamodels.sighting import Sighting
from ..core.utils import convert_date_format, parse_csv_list

SCRIPT_NAME = "Create Sighting"


class CreateSightingParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    from_object_id: str = Field(
        description="Specify source object ID",
    )
    to_object_id: str = Field(
        description="Specify target object ID",
    )
    description: str | None = Field(
        description="Specify sighting description",
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
    labels: list[str] | None = Field(
        description="Specify entity's labels",
        default=None,
    )
    marking: str | None = Field(
        description="Specify marking for the sighting",
        default=None,
    )

    @field_validator("labels", mode="before")
    @classmethod
    def _parse_labels(cls, value: str | None) -> list[str] | None:
        """Convert a comma-separated labels string into a cleaned labels list.

        Args:
            value: Raw labels parameter from the action form.

        Returns:
            A list of trimmed labels, or None when no labels were provided.
        """
        return parse_csv_list(value) if value else None

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


class CreateSighting(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateSightingParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateSightingParameters(  # type: ignore[assignment]
            from_object_id=raw_params.get("From Object Id"),
            to_object_id=raw_params.get("To Object Id"),
            description=raw_params.get("Description"),
            first_seen=raw_params.get("First Seen"),
            last_seen=raw_params.get("Last Seen"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
        )

    def _perform_action(self, _=None) -> None:
        """Create a Sighting in OpenCTI for the provided source and target objects.
        On success it stores the new sighting details in output fields;
        on failure an exception propagates and the framework marks the action as failed.
        """
        sighting = Sighting(
            from_id=self.params.from_object_id,
            to_id=self.params.to_object_id,
            description=self.params.description,
            first_seen=self.params.first_seen,
            last_seen=self.params.last_seen,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
        )
        result = self.api_client.create_sighting(sighting)

        self.output_message = f"Sighting successfully created with ID {result.id}"

        self.json_results = result.json() or {}


def main() -> None:
    """Action entry point."""
    CreateSighting(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
