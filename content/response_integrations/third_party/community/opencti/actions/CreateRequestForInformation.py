from __future__ import annotations

from datetime import datetime, timezone

from pydantic import AwareDatetime, Field, field_validator

from ..core.base_action import BaseAction
from ..core.base_action_parameters import BaseActionParameters
from ..core.datamodels.request_for_information import RequestForInformation
from ..core.utils import convert_date_format, parse_csv_list

SCRIPT_NAME = "Create Request for Information"


class CreateRequestForInformationParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    name: str = Field(
        description="Specify the name of the Request For Information",
    )
    description: str | None = Field(
        description="Specify the description of the Request For Information",
        default=None,
    )
    created: AwareDatetime = Field(
        description="Specify the creation date of the Request For Information in format YYYY-MM-DDTHH:mm:ssZ",
        default_factory=lambda: datetime.now(tz=timezone.utc),
    )
    severity: str | None = Field(
        description="Specify the severity of the Request For Information",
        default=None,
    )
    rfi_type: str | None = Field(
        description="Specify the type of the Request For Information",
        default=None,
    )
    labels: list[str] | None = Field(
        description="Specify the labels of the Request For Information as a comma-separated string",
        default=None,
    )
    marking: str | None = Field(
        description="Specify the marking of the Request For Information",
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


class CreateRequestForInformation(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateRequestForInformationParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateRequestForInformationParameters(  # type: ignore[assignment]
            name=raw_params.get("Name"),
            description=raw_params.get("Description"),
            rfi_type=raw_params.get("Type"),
            severity=raw_params.get("Severity"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
            created=raw_params.get("Created At"),
        )

    def _perform_action(self, _=None) -> None:
        """Create a Request for Information case in OpenCTI from input values.
        On success it updates output fields with the created case details;
        on failure an exception propagates and the framework marks the action as failed.
        """
        request_for_information = RequestForInformation(
            name=self.params.name,
            description=self.params.description,
            information_types=[self.params.rfi_type] if self.params.rfi_type else None,
            priority=None,
            severity=self.params.severity,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
            created=self.params.created,
            created_by=None,
        )
        result = self.api_client.create_request_for_information(request_for_information)

        self.output_message = (
            f"Request for Information successfully created with ID {result.id}"
        )

        self.json_results = result.json() or {}


def main() -> None:
    """Entry point for executing the "Create Request for Information" action script.

    This function initializes the CreateRequestForInformation class with
    the predefined script name and triggers its execution.
    """
    CreateRequestForInformation(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
