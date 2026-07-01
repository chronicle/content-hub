from __future__ import annotations

from typing import Literal

from core.base_action import BaseAction
from core.base_action_parameters import BaseActionParameters
from core.datamodels.observable import Observable
from core.utils import is_ipv4, parse_csv_list
from pydantic import Field, field_validator

SCRIPT_NAME = "Create Observable"


class CreateObservableParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    observable_type: Literal[
        "Domain Name",
        "URL",
        "Hostname",
        "Email Subject",
        "Email Addr",
        "IP",
        "Hash",
    ] = Field(
        description="Specify the type of the observable",
    )
    observable_value: str = Field(
        description="Specify the value of the observable",
    )
    description: str | None = Field(
        description="Specify the description of the observable",
        default=None,
    )
    score: int | None = Field(
        description="Specify the threat score of the observable (0-100)",
        default=None,
        ge=0,
        le=100,
    )
    labels: list[str] | None = Field(
        description="Specify the labels of the observable as a comma-separated string",
        default=None,
    )
    marking: str | None = Field(
        description="Specify the marking of the observable",
        default=None,
    )
    create_indicator: bool = Field(
        description="Create an indicator from the created observable",
        default=False,
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


class CreateObservable(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateObservableParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateObservableParameters(  # type: ignore[assignment]
            observable_type=raw_params.get("Observable Type"),
            observable_value=raw_params.get("Observable Value"),
            description=raw_params.get("Description"),
            score=raw_params.get("Score"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
            create_indicator=raw_params.get("Create Indicator"),
        )

    def _perform_action(self, _=None) -> None:
        """Create an Observable in OpenCTI afrom input values.
        On success it stores the created observable details in output fields;
        on failure an exception propagates and the framework marks the action as failed.
        """
        observable_type = None
        match self.params.observable_type:
            case "Domain Name":
                observable_type = "Domain-Name"
            case "URL":
                observable_type = "Url"
            case "Hostname":
                observable_type = "Hostname"
            case "Email Subject":
                observable_type = "Email-Message"
            case "Email Addr":
                observable_type = "Email-Addr"
            case "IP":
                value = self.params.observable_value
                if value:
                    observable_type = "IPv4-Addr" if is_ipv4(value) else "IPv6-Addr"
            case "Hash":
                observable_type = "StixFile"

        observable = Observable(
            type=observable_type,  # type: ignore[arg-type]
            value=self.params.observable_value,
            description=self.params.description,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
            score=self.params.score,
            create_indicator=self.params.create_indicator,
        )
        result = self.api_client.create_observable(observable)

        self.output_message = f"Observable successfully created with ID {result.id}"

        self.json_results = result.json() or {}


def main() -> None:
    """Entry point for executing the "Create Observable" action script."""
    CreateObservable(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
