from __future__ import annotations

from core.base_action import BaseAction
from core.base_action_parameters import BaseActionParameters
from core.datamodels.threat_actor_group import ThreatActorGroup
from core.utils import parse_csv_list
from pydantic import Field, field_validator

SCRIPT_NAME = "Create Threat Actor Group"


class CreateThreatActorGroupParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    name: str = Field(
        description="Specify the name of the threat actor group",
    )
    description: str | None = Field(
        description="Specify threat actor group description",
        default=None,
    )
    threat_actor_types: list[str] | None = Field(
        description="Specify threat actor types",
        default=None,
    )
    labels: list[str] | None = Field(
        description="Specify entity's labels",
        default=None,
    )
    marking: str | None = Field(
        description="Specify marking for the threat actor group",
        default=None,
    )

    @field_validator("threat_actor_types", "labels", mode="before")
    @classmethod
    def _parse_csv(cls, value: str | None) -> list[str] | None:
        """Convert a comma-separated string into a cleaned list of values.

        Args:
            value: Raw comma-separated parameter from the action form.

        Returns:
            A list of trimmed items, or None when no value was provided.
        """
        return parse_csv_list(value) if value else None


class CreateThreatActorGroup(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateThreatActorGroupParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateThreatActorGroupParameters(  # type: ignore[assignment]
            name=raw_params.get("Name"),
            description=raw_params.get("Description"),
            threat_actor_types=raw_params.get("Threat Actor Types"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
        )

    def _perform_action(self, _=None) -> None:
        """Create a Threat Actor Group in OpenCTI from input values.
        On success it returns the created group details in output fields;
        on failure an exception propagates and the framework marks the action as failed.
        """
        threat_actor_group = ThreatActorGroup(
            name=self.params.name,
            description=self.params.description,
            threat_actor_types=self.params.threat_actor_types,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
        )
        result = self.api_client.create_threat_actor_group(threat_actor_group)

        self.output_message = (
            f"Threat Actor Group successfully created with ID {result.id}"
        )

        self.json_results = result.json() or {}


def main() -> None:
    """Action entry point."""
    CreateThreatActorGroup(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
