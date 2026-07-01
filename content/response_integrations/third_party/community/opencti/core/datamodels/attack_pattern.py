import pycti
from core.datamodels.base_octi_object import BaseOCTIObject


class AttackPattern(BaseOCTIObject):
    """Represent the AttackPattern model."""

    name: str
    description: str | None = None
    external_id: str | None = None
    labels: list[str] | None = None
    markings: list[str] | None = None

    def _compute_stix_id(self) -> str:
        """Build a deterministic STIX ID for the attack pattern.
        Returns:
            The generated STIX identifier.
        """
        return pycti.AttackPattern.generate_id(
            name=self.name,
            x_mitre_id=self.external_id,
        )

    def to_input_variables(self) -> dict:
        """Serialize the model into OpenCTI GraphQL payload.
        Returns:
            A dictionary matching OpenCTI input variable names.
        """
        input_variables = {
            "stix_id": self._compute_stix_id(),
            "name": self.name,
            "description": self.description,
            "x_mitre_id": self.external_id,
            "objectLabel": self.labels,
            "objectMarking": self._compute_markings_ids(),
        }
        return self._keep_set_variables_only(input_variables)
