from __future__ import annotations

from abc import ABC, abstractmethod

from pycti import MarkingDefinition
from pydantic import BaseModel, ConfigDict


class BaseOCTIObject(BaseModel, ABC):
    """Represent the BaseOCTIObject model."""

    model_config = ConfigDict(
        # Forbid extra fields that are not defined in the model, raising a validation error
        extra="forbid",
        # Make the model mutable to allow modifications
        frozen=False,
        # Validate field values on assignment to ensure they conform to the field types and constraints
        validate_assignment=True,
        # Validate default values to ensure they conform to the field types and constraints
        validate_default=True,
    )

    @abstractmethod
    def _compute_stix_id(self) -> str:
        """Compute the STIX ID of the entity, based on its content.

        The 'generate_id' methods from `pycti` must be used to ensure the ID is deterministic.

        Returns:
            A string representing the STIX ID of the entity.
        """
        raise NotImplementedError(
            "Subclasses of `BaseOCTIObject` must implement the '_compute_stix_id' method."
        )

    @abstractmethod
    def to_input_variables(self) -> dict:
        """Convert the entity's attributes into a dictionary of input variables for OpenCTI client.

        The returned dictionary should include all relevant fields, with keys matching the expected
        input variable names for OpenCTI GraphQL requests. Fields that are not set (i.e., have a value
        of None) should be omitted from the dictionary to avoid sending them to OpenCTI.

        Returns:
            A dictionary containing the entity's attributes as input variables for OpenCTI.
        """
        raise NotImplementedError(
            "Subclasses of `BaseOCTIObject` must implement the 'to_input_variables' method."
        )

    def _compute_markings_ids(self) -> list[str] | None:
        """Compute the list of marking IDs associated with the entity.

        The 'markings' property is optional and can be None.

        Returns:
            A list of strings representing the marking IDs, or None if no markings are set.
        """
        if markings := getattr(self, "markings", []):
            return [
                MarkingDefinition.generate_id("TLP", definition=marking)
                for marking in markings
            ]

        return None

    @classmethod
    def _keep_set_variables_only(cls, variables: dict) -> dict:
        """Filter out variables that are not set (i.e., have a value of None) to avoid sending them to OpenCTI.

        Args:
            variables: A dictionary of variables to filter.

        Returns:
            A filtered dictionary containing only the variables that are set
            (i.e., have a value other than None).
        """
        return {key: value for key, value in variables.items() if value is not None}
