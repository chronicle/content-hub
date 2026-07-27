from __future__ import annotations

import pycti

from ..datamodels.base_octi_object import BaseOCTIObject


class ThreatActorGroup(BaseOCTIObject):
    """Represent the ThreatActorGroup model."""

    name: str
    description: str | None = None
    threat_actor_types: list[str] | None = None
    labels: list[str] | None = None
    markings: list[str] | None = None

    def _compute_stix_id(self) -> str:
        """Build a deterministic STIX ID for this object.
        Returns:
            The generated STIX identifier.
        """
        return pycti.ThreatActorGroup.generate_id(name=self.name)

    def to_input_variables(self) -> dict:
        """Serialize the model into OpenCTI GraphQL payload.
        Returns:
            A dictionary matching OpenCTI input variable names.
        """
        input_variables = {
            "stix_id": self._compute_stix_id(),
            "name": self.name,
            "description": self.description,
            "threat_actor_types": self.threat_actor_types,
            "objectLabel": self.labels,
            "objectMarking": self._compute_markings_ids(),
        }
        return self._keep_set_variables_only(input_variables)
