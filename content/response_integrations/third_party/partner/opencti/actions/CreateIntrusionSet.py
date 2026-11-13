from __future__ import annotations

from pydantic import Field, field_validator

from ..core.base_action import BaseAction
from ..core.base_action_parameters import BaseActionParameters
from ..core.datamodels.intrusion_set import IntrusionSet
from ..core.utils import parse_csv_list

SCRIPT_NAME = "Create Intrusion Set"


class CreateIntrusionSetParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    name: str = Field(
        description="Specify the name of the intrusion set",
    )
    description: str | None = Field(
        description="Specify intrusion set description",
        default=None,
    )
    labels: list[str] | None = Field(
        description="Specify entity's labels",
        default=None,
    )
    marking: str | None = Field(
        description="Specify marking for the intrusion set",
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


class CreateIntrusionSet(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateIntrusionSetParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateIntrusionSetParameters(  # type: ignore[assignment]
            name=raw_params.get("Name"),
            description=raw_params.get("Description"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
        )

    def _perform_action(self, _=None) -> None:
        """Create an Intrusion Set in OpenCTI from input values.
        On success it writes the created intrusion set details to output fields;
        on failure an exception propagates and the framework marks the action as failed.
        """
        intrusion_set = IntrusionSet(
            name=self.params.name,
            description=self.params.description,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
        )
        result = self.api_client.create_intrusion_set(intrusion_set)

        self.output_message = f"Intrusion Set successfully created with ID {result.id}"

        self.json_results = result.json() or {}


def main() -> None:
    """Action entry point."""
    CreateIntrusionSet(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
