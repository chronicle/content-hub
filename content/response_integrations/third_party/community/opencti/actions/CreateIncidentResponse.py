from __future__ import annotations

from datetime import datetime, timezone

from core.base_action import BaseAction
from core.base_action_parameters import BaseActionParameters
from core.datamodels.incident_response import IncidentResponse
from core.utils import convert_date_format, parse_csv_list
from pydantic import AwareDatetime, Field, field_validator

SCRIPT_NAME = "Create Incident Response"


class CreateIncidentResponseParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    name: str = Field(
        description="Specify the name of the Incident Response",
    )
    description: str | None = Field(
        description="Specify the description of the Incident Response",
        default=None,
    )
    created: AwareDatetime = Field(
        description=(
            "Specify the creation date of the Incident Response in format YYYY-MM-DDTHH:mm:ssZ"
        ),
        default_factory=lambda: datetime.now(tz=timezone.utc),
    )
    severity: str | None = Field(
        description="Specify the severity of the Incident Response",
        default=None,
    )
    priority: str | None = Field(
        description="Specify the priority of the Incident Response",
        default=None,
    )
    response_type: str | None = Field(
        description="Specify the type of the Incident Response",
        default=None,
    )
    labels: list[str] | None = Field(
        description=(
            "Specify the labels of the Incident Response as a comma-separated string"
        ),
        default=None,
    )
    marking: str | None = Field(
        description="Specify the marking of the Incident Response",
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

    @field_validator("created", mode="before")
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


class CreateIncidentResponse(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateIncidentResponseParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateIncidentResponseParameters(  # type: ignore[assignment]
            name=raw_params.get("Name"),
            description=raw_params.get("Description"),
            created=raw_params.get("Created At"),
            severity=raw_params.get("Severity"),
            priority=raw_params.get("Priority"),
            response_type=raw_params.get("Type"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
        )

    def _perform_action(self, _=None) -> None:
        """Create an Incident Response case in OpenCTI from input values.
        On success it returns the created case details in output fields;
        on failure an exception propagates and the framework marks the action as failed.
        """
        incident_response = IncidentResponse(
            name=self.params.name,
            description=self.params.description,
            response_types=(
                [self.params.response_type] if self.params.response_type else None
            ),
            priority=self.params.priority,
            severity=self.params.severity,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
            created=self.params.created,
            created_by=None,
        )
        result = self.api_client.create_incident_response(incident_response)

        self.output_message = (
            f"Incident Response successfully created with ID {result.id}"
        )

        self.json_results = result.json() or {}


def main() -> None:
    """Entry point for executing the "Create Incident Response" action script."""
    CreateIncidentResponse(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
