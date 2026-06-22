from __future__ import annotations

from datetime import datetime, timezone

from core.base_action import BaseAction
from core.base_action_parameters import BaseActionParameters
from core.datamodels.incident import Incident
from core.utils import convert_date_format, parse_csv_list
from pydantic import AwareDatetime, Field, field_validator

SCRIPT_NAME = "Create Incident"


class CreateIncidentParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    name: str = Field(
        description="Specify the name of the Incident",
    )
    description: str | None = Field(
        description="Specify the description of the Incident",
        default=None,
    )
    created: AwareDatetime = Field(
        description="Specify the creation date of the Incident in format YYYY-MM-DDTHH:mm:ssZ",
        default_factory=lambda: datetime.now(tz=timezone.utc),
    )
    severity: str | None = Field(
        description="Specify the severity of the Incident",
        default=None,
    )
    incident_type: str | None = Field(
        description="Specify the type of the Incident",
        default=None,
    )
    labels: list[str] | None = Field(
        description="Specify the labels of the Incident as a comma-separated string",
        default=None,
    )
    marking: str | None = Field(
        description="Specify the marking of the Incident",
        default=None,
    )

    @field_validator("labels", mode="before")
    @classmethod
    def _parse_labels(cls, value: str | None) -> list[str] | None:
        return parse_csv_list(value) if value else None

    @field_validator("created", mode="before")
    @classmethod
    def _parse_datetimes(cls, value: str | None) -> str | None:
        if not isinstance(value, str) or not value:
            return value

        return convert_date_format(value)


class CreateIncident(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateIncidentParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateIncidentParameters(  # type: ignore[assignment]
            name=raw_params.get("Name"),
            description=raw_params.get("Description"),
            incident_type=raw_params.get("Type"),
            severity=raw_params.get("Severity"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
            created=raw_params.get("Created At"),
        )

    def _perform_action(self, _=None) -> None:
        """Create an Incident in OpenCTI from the validated incident parameters.
        On success it updates the output message and JSON result with the created incident;
        on failure an exception propagates and the framework marks the action as failed.
        """
        incident = Incident(
            name=self.params.name,
            description=self.params.description,
            incident_type=self.params.incident_type,
            priority=None,
            severity=self.params.severity,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
            created=self.params.created,
            created_by=None,
        )
        result = self.api_client.create_incident(incident)

        self.output_message = f"Incident successfully created with ID {result.id}"

        self.json_results = result.json() or {}


def main() -> None:
    """Entry point for executing the "Create Incident" action script.

    This function initialized the CreateIncident class with
    the predefined script name and triggers its execution.
    """
    CreateIncident(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
