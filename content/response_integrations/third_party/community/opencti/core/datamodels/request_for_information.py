import pycti
from core.datamodels.base_octi_object import BaseOCTIObject
from pydantic import AwareDatetime


class RequestForInformation(BaseOCTIObject):
    name: str
    description: str | None = None
    information_types: list[str] | None = None
    priority: str | None = None
    severity: str | None = None
    labels: list[str] | None = None
    markings: list[str] | None = None
    created_by: str | None = None
    created: AwareDatetime | None = None

    def _compute_stix_id(self) -> str:
        return pycti.CaseRfi.generate_id(name=self.name, created=self.created)

    def to_input_variables(self) -> dict:
        input = {
            "stix_id": self._compute_stix_id(),
            "name": self.name,
            "description": self.description,
            "information_types": self.information_types,
            "priority": self.priority,
            "severity": self.severity,
            "objectLabel": self.labels,
            "objectMarking": self._compute_markings_ids(),
            "createdBy": self.created_by,
            "created": self.created.isoformat() if self.created else None,
        }

        return self._keep_set_variables_only(input)
