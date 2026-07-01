from __future__ import annotations

from core.base_action import BaseAction
from core.base_action_parameters import BaseActionParameters
from core.datamodels.indicator import Indicator
from core.utils import convert_date_format, parse_csv_list
from pydantic import AwareDatetime, Field, field_validator

SCRIPT_NAME = "Create Indicator"


class CreateIndicatorParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    name: str = Field(
        description="Specify the name of the indicator",
    )
    pattern: str = Field(
        description="Specify the STIX pattern",
    )
    description: str | None = Field(
        description="Specify indicator description",
        default=None,
    )
    valid_from: AwareDatetime | None = Field(
        description="Specify valid from date (ISO 8601 format)",
        default=None,
    )
    valid_until: AwareDatetime | None = Field(
        description="Specify valid until date (ISO 8601 format)",
        default=None,
    )
    score: int | None = Field(
        description="Specify the score of the indicator",
        default=None,
        ge=0,
        le=100,
    )
    labels: list[str] | None = Field(
        description="Specify entity's labels",
        default=None,
    )
    marking: str | None = Field(
        description="Specify marking for the indicator",
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

    @field_validator("valid_from", "valid_until", mode="before")
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


class CreateIndicator(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateIndicatorParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateIndicatorParameters(  # type: ignore[assignment]
            name=raw_params.get("Name"),
            pattern=raw_params.get("Pattern"),
            description=raw_params.get("Description"),
            valid_from=raw_params.get("Valid From"),
            valid_until=raw_params.get("Valid Until"),
            score=raw_params.get("Score"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
        )

    def _perform_action(self, _=None) -> None:
        """Create an Indicator in OpenCTI from the provided STIX pattern and metadata.
        On success it stores the indicator ID and JSON result;
        on failure an exception propagates and the framework marks the action as failed.
        """
        indicator = Indicator(
            name=self.params.name,
            pattern=self.params.pattern,
            description=self.params.description,
            valid_from=self.params.valid_from,
            valid_until=self.params.valid_until,
            score=self.params.score,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
        )
        result = self.api_client.create_indicator(indicator)

        self.output_message = f"Indicator successfully created with ID {result.id}"

        self.json_results = result.json() or {}


def main() -> None:
    """Action entry point."""
    CreateIndicator(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
