from __future__ import annotations

from pydantic import AwareDatetime, Field, field_validator

from ..core.base_action import BaseAction
from ..core.base_action_parameters import BaseActionParameters
from ..core.datamodels.report import Report
from ..core.utils import convert_date_format, parse_csv_list

SCRIPT_NAME = "Create Report"


class CreateReportParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    name: str = Field(
        description="Specify the name of the report",
    )
    publication_date: AwareDatetime = Field(
        description="Specify publication date in ISO 8601 format"
    )
    description: str | None = Field(
        description="Specify description of the report",
        default=None,
    )
    report_types: list[str] | None = Field(
        description="Specify report types as comma-separated values",
        default=None,
    )
    labels: list[str] | None = Field(
        description="Specify entity's labels",
        default=None,
    )
    marking: str | None = Field(
        description="Specify marking for the report",
        default=None,
    )

    @field_validator("report_types", "labels", mode="before")
    @classmethod
    def _parse_csv(cls, value: str | None) -> list[str] | None:
        """Convert a comma-separated string into a cleaned list of values.

        Args:
            value: Raw comma-separated parameter from the action form.

        Returns:
            A list of trimmed items, or None when no value was provided.
        """
        return parse_csv_list(value) if value else None

    @field_validator("publication_date", mode="before")
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


class CreateReport(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateReportParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateReportParameters(  # type: ignore[assignment]
            name=raw_params.get("Name"),
            publication_date=raw_params.get("Publication Date"),
            description=raw_params.get("Description"),
            report_types=raw_params.get("Report Types"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
        )

    def _perform_action(self, _=None) -> None:
        """Create a Report in OpenCTI from input values.
        On success it stores the report ID and JSON result in output fields;
        on failure an exception propagates and the framework marks the action as failed.
        """
        report = Report(
            name=self.params.name,
            published=self.params.publication_date,
            description=self.params.description,
            report_types=self.params.report_types,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
        )
        result = self.api_client.create_report(report)

        self.output_message = f"Report successfully created with ID {result.id}"

        self.json_results = result.json() or {}


def main() -> None:
    """Action entry point."""
    CreateReport(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
