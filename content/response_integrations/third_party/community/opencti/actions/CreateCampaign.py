from __future__ import annotations

from core.base_action import BaseAction
from core.base_action_parameters import BaseActionParameters
from core.datamodels.campaign import Campaign
from core.utils import convert_date_format, parse_csv_list
from pydantic import AwareDatetime, Field, field_validator

SCRIPT_NAME = "Create Campaign"


class CreateCampaignParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    name: str = Field(
        description="Specify the name of the campaign",
    )
    description: str | None = Field(
        description="Specify campaign description",
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
        description="Specify marking for the campaign",
        default=None,
    )

    @field_validator("labels", mode="before")
    @classmethod
    def _parse_labels(cls, value: str | None) -> list[str] | None:
        return parse_csv_list(value) if value else None

    @field_validator("first_seen", "last_seen", mode="before")
    @classmethod
    def _parse_datetimes(cls, value: str | None) -> str | None:
        if not isinstance(value, str) or not value:
            return value

        return convert_date_format(value)


class CreateCampaign(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> CreateCampaignParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateCampaignParameters(  # type: ignore[assignment]
            name=raw_params.get("Name"),
            description=raw_params.get("Description"),
            first_seen=raw_params.get("First Seen"),
            last_seen=raw_params.get("Last Seen"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
        )

    def _perform_action(self, _=None) -> None:
        """Create a Campaign in OpenCTI using the mapped campaign model.
        On success it reports the created campaign ID and JSON result;
        on failure an exception propagates and the framework marks the action as failed.
        """
        campaign = Campaign(
            name=self.params.name,
            description=self.params.description,
            first_seen=self.params.first_seen,
            last_seen=self.params.last_seen,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
        )
        result = self.api_client.create_campaign(campaign)

        self.output_message = f"Campaign successfully created with ID {result.id}"

        self.json_results = result.json() or {}


def main() -> None:
    CreateCampaign(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
