from __future__ import annotations

from typing import TYPE_CHECKING

from core.base_action import BaseAction
from core.base_action_parameters import BaseActionParameters
from core.datamodels.observable import Observable
from core.utils import is_ipv4, parse_csv_list
from pydantic import Field, field_validator
from TIPCommon.base.action import EntityTypesEnum

if TYPE_CHECKING:
    from TIPCommon.types import Entity

SCRIPT_NAME = "Create Observables"

SUPPORTED_ENTITY_TYPES = [
    EntityTypesEnum.ADDRESS,
    EntityTypesEnum.DOMAIN,
    EntityTypesEnum.EMAIL_MESSAGE,
    EntityTypesEnum.FILE_HASH,
    EntityTypesEnum.FILE_NAME,
    EntityTypesEnum.HOST_NAME,
    EntityTypesEnum.URL,
    EntityTypesEnum.USER,
]

ENTITY_TYPE_TO_OPENCTI_SCO_TYPE = {
    EntityTypesEnum.ADDRESS: "IPv4-Addr",  # may be overridden to IPv6-Addr based on value
    EntityTypesEnum.DOMAIN: "Domain-Name",
    EntityTypesEnum.EMAIL_MESSAGE: "Email-Message",
    EntityTypesEnum.FILE_HASH: "StixFile",
    EntityTypesEnum.FILE_NAME: "File-Name",
    EntityTypesEnum.HOST_NAME: "Hostname",
    EntityTypesEnum.URL: "Url",
    EntityTypesEnum.USER: "Email-Addr",
}


class CreateObservablesParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    description: str | None = Field(
        description="Specify the description of the observables",
        default=None,
    )
    score: int | None = Field(
        description="Specify the threat score of the observables (0-100)",
        default=None,
        ge=0,
        le=100,
    )
    labels: list[str] | None = Field(
        description="Specify the labels of the observables as a comma-separated string",
        default=None,
    )
    marking: str | None = Field(
        description="Specify the marking of the observables",
        default=None,
    )
    create_indicator: bool = Field(
        description="Create an indicator from each created observable",
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


class CreateObservables(BaseAction):
    """Create STIX cyber observables in OpenCTI from the action's target entities.

    Entity iteration is handled by the SOAR framework: this action only maps and
    creates an observable for each supported entity through _perform_action.
    """

    @property
    def params(self) -> CreateObservablesParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = CreateObservablesParameters(  # type: ignore[assignment]
            description=raw_params.get("Description"),
            score=raw_params.get("Score"),
            labels=raw_params.get("Labels"),
            marking=raw_params.get("Marking"),
            create_indicator=raw_params.get("Create Indicator"),
        )

    def _get_entity_types(self) -> list[EntityTypesEnum]:
        """Return the entity types supported by this action.

        Returns:
            list[EntityTypesEnum]: Entity types eligible for observable creation.
        """
        return SUPPORTED_ENTITY_TYPES

    def _resolve_observable_type(self, current_entity: Entity) -> str:  # type: ignore[type-var]
        """Map a SOAR entity type to its OpenCTI observable type.

        Args:
            current_entity: The SOAR entity currently being processed.

        Returns:
            The OpenCTI observable type to create.
        """
        entity_type = EntityTypesEnum(current_entity.entity_type)

        if entity_type == EntityTypesEnum.ADDRESS:
            return (
                "IPv4-Addr"
                if is_ipv4(current_entity.original_identifier)
                else "IPv6-Addr"
            )

        return ENTITY_TYPE_TO_OPENCTI_SCO_TYPE[entity_type]

    def _perform_action(self, current_entity: Entity) -> None:  # type: ignore[type-var]
        """Create one observable in OpenCTI for the current entity.

        This method runs once per entity; the base action flow calls it in a
        loop of all eligible target entities.
        On success the created observable JSON is stored under the entity's identifier.
        On failure an exception propagates and the framework marks this entity as failed.

        Args:
            current_entity: The SOAR entity currently being processed.
        """
        identifier = current_entity.original_identifier
        observable_type = self._resolve_observable_type(current_entity)

        observable = Observable(
            type=observable_type,  # type: ignore[arg-type]
            value=identifier,
            description=self.params.description,
            labels=self.params.labels,
            markings=[self.params.marking] if self.params.marking else None,
            score=self.params.score,
            create_indicator=self.params.create_indicator,
        )

        result = self.api_client.create_observable(observable)

        self._created_identifiers.append(identifier)
        self.json_results[identifier] = result.json() or {}


def main() -> None:
    """Action entry point."""
    CreateObservables(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
