import pycti
from core.datamodels.base_octi_object import BaseOCTIObject
from pydantic import AwareDatetime


class IncidentResponse(BaseOCTIObject):
    """Represent the IncidentResponse model."""
    name: str
    description: str | None = None
    response_types: list[str] | None = None
    priority: str | None = None
    severity: str | None = None
    labels: list[str] | None = None
    markings: list[str] | None = None
    created_by: str | None = None
    created: AwareDatetime | None = None
    
    def _compute_stix_id(self) -> str:
        """Build a deterministic STIX ID for this object.
        Returns:
            The generated STIX identifier.
        """
        return pycti.CaseIncident.generate_id(name=self.name, created=self.created)
    
    def to_input_variables(self) -> dict:
        """Serialize the model into OpenCTI GraphQL payload.
        Returns:
            A dictionary matching OpenCTI input variable names.
        """
        input = {
            "stix_id": self._compute_stix_id(),
            "name": self.name,
            "description": self.description,
            "response_types": self.response_types,
            "priority": self.priority,
            "severity": self.severity,
            "objectLabel": self.labels,
            "objectMarking": self._compute_markings_ids(),
            "createdBy": self.created_by,
            "created": self.created.isoformat() if self.created else None,
        }
        return self._keep_set_variables_only(input)
