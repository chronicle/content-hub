from __future__ import annotations

from typing import Literal

from core.base_action import BaseAction
from core.base_action_parameters import BaseActionParameters
from pydantic import Field

SCRIPT_NAME = "Add Object to Container"

CONTAINER_TYPE_TO_OPENCTI_ENTITY_TYPE: dict[str, str] = {
    "Report": "Report",
    "Incident Response Case": "Case-Incident",
    "Request for Information": "Case-Rfi",
    "Request for Takedown": "Case-Rft",
    "Grouping": "Grouping",
}


class AddObjectToContainerParameters(BaseActionParameters):
    """Represent the expected action parameters as defined
    in the YAML file and Google SOAR UI.
    """

    container_type: Literal[
        "Report",
        "Incident Response Case",
        "Request for Information",
        "Request for Takedown",
        "Grouping",
    ] = Field(
        description="Specify the container type",
    )
    container_id: str = Field(
        description="Specify the container id",
    )
    object_id: str = Field(
        description="Specify the object id",
    )


class AddObjectToContainer(BaseAction):
    """Implementation of Google SOAR action.
    It validates user input, performs the requested operation, and exposes structured results.
    """

    @property
    def params(self) -> AddObjectToContainerParameters:
        """Returns the action's parameters. Overridden for typing purposes only."""
        return super().params  # type: ignore[return-value]

    def _validate_params(self) -> None:
        """Parse and validate user input parameters."""
        raw_params = self.soar_action.parameters
        self._params = AddObjectToContainerParameters(  # type: ignore[assignment]
            container_type=raw_params.get("Container Type"),
            container_id=raw_params.get("Container Id"),
            object_id=raw_params.get("Object Id"),
        )

    def _perform_action(self, _=None) -> None:
        """Add the provided object to the selected OpenCTI container.
        On success the container update and JSON result are set;
        on failure an exception propagates and the framework marks the action as failed.
        """
        container_type = CONTAINER_TYPE_TO_OPENCTI_ENTITY_TYPE.get(
            self.params.container_type
        )
        result = self.api_client.add_object_to_container(
            container_type=container_type,  # type: ignore[arg-type]
            container_id=self.params.container_id,
            object_id=self.params.object_id,
        )

        self.output_message = (
            f"Object {self.params.object_id} successfully added to "
            f"{self.params.container_type} with id {self.params.container_id}"
        )

        self.json_results = result.json()


def main() -> None:
    """Entry point for executing the "Add Object to Container" action script."""
    AddObjectToContainer(SCRIPT_NAME).run()


if __name__ == "__main__":
    main()
