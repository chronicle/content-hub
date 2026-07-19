from __future__ import annotations

import pycti
from pydantic import AwareDatetime

from ..datamodels.base_octi_object import BaseOCTIObject


class Sighting(BaseOCTIObject):
    """Represent the Sighting model."""

    from_id: str
    to_id: str
    count: int = 1
    description: str | None = None
    first_seen: AwareDatetime | None = None
    last_seen: AwareDatetime | None = None
    labels: list[str] | None = None
    markings: list[str] | None = None

    def _compute_stix_id(self) -> str:
        """Build a deterministic STIX ID for this object.
        Returns:
            The generated STIX identifier.
        """
        return pycti.StixSightingRelationship.generate_id(
            sighting_of_ref=self.to_id,
            where_sighted_refs=[self.from_id],
            first_seen=self.first_seen.isoformat() if self.first_seen else None,
            last_seen=self.last_seen.isoformat() if self.last_seen else None,
        )

    def to_input_variables(self) -> dict:
        """Serialize the model into OpenCTI GraphQL payload.
        Returns:
            A dictionary matching OpenCTI input variable names.
        """
        input_variables = {
            "stix_id": self._compute_stix_id(),
            "fromId": self.from_id,
            "toId": self.to_id,
            "count": self.count,
            "description": self.description,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "objectLabel": self.labels,
            "objectMarking": self._compute_markings_ids(),
        }
        return self._keep_set_variables_only(input_variables)
