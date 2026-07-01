from __future__ import annotations

from core.base_action import BaseAction
from core.base_action_parameters import BaseActionParameters
from core.datamodels.attack_pattern import AttackPattern
from core.utils import parse_csv_list
from pydantic import Field, field_validator

SCRIPT_NAME = "Create Attack Pattern"


class CreateAttackPatternParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    name: str = Field(
        description="Specify the name of the attack pattern",
    )
    description: str | None = Field(
        description="Specify description of the attack pattern",
        default=None,
    )
    external_id: str | None = Field(
        description="Specify MITRE ATT&CK external id",
        default=None,
    )
    labels: list[str] | None = Field(
        description="Specify entity's labels",
        default=None,
    )
    marking: str | None = Field(
        description="Specify marking for the attack pattern",
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


class CreateAttackPattern(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateAttackPatternParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateAttackPatternParameters(  # type: ignore[assignment]
            name=raw_params.get("Name"),
            description=raw_params.get("Description"),
            external_id=raw_params.get("External Id"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
        )

    def _perform_action(self, _=None) -> None:
        """Create an Attack Pattern in OpenCTI from input values.
        On success it stores the created object details in output fields;
        on failure an exception propagates and the framework marks the action as failed.
        """
        attack_pattern = AttackPattern(
            name=self.params.name,
            description=self.params.description,
            external_id=self.params.external_id,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
        )
        result = self.api_client.create_attack_pattern(attack_pattern)

        self.output_message = f"Attack Pattern successfully created with ID {result.id}"

        self.json_results = result.json() or {}


def main() -> None:
    """Action entry point."""
    CreateAttackPattern(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
