from __future__ import annotations

import pycti
from pydantic import AwareDatetime

from ..datamodels.base_octi_object import BaseOCTIObject


class Relationship(BaseOCTIObject):
    """Represent the Relationship model."""

    relationship_type: str
    source_ref: str
    target_ref: str
    description: str | None = None
    first_seen: AwareDatetime | None = None
    last_seen: AwareDatetime | None = None
    markings: list[str] | None = None

    def _compute_stix_id(self) -> str:
        """Build a deterministic STIX ID for this object.
        Returns:
            The generated STIX identifier.
        """
        return pycti.StixCoreRelationship.generate_id(
            relationship_type=self.relationship_type,
            source_ref=self.source_ref,
            target_ref=self.target_ref,
            start_time=self.first_seen.isoformat() if self.first_seen else None,
            stop_time=self.last_seen.isoformat() if self.last_seen else None,
        )

    def to_input_variables(self) -> dict:
        """Serialize the model into OpenCTI GraphQL payload.
        Returns:
            A dictionary matching OpenCTI input variable names.
        """
        input_variables = {
            "stix_id": self._compute_stix_id(),
            "fromId": self.source_ref,
            "toId": self.target_ref,
            "relationship_type": self.relationship_type,
            "description": self.description,
            "start_time": self.first_seen.isoformat() if self.first_seen else None,
            "stop_time": self.last_seen.isoformat() if self.last_seen else None,
            "objectMarking": self._compute_markings_ids(),
        }
        return self._keep_set_variables_only(input_variables)
