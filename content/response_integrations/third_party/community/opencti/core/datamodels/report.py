import pycti
from core.datamodels.base_octi_object import BaseOCTIObject
from pydantic import AwareDatetime


class Report(BaseOCTIObject):
    """Represent the Report model."""
    name: str
    published: AwareDatetime
    description: str | None = None
    report_types: list[str] | None = None
    labels: list[str] | None = None
    markings: list[str] | None = None
    
    def _compute_stix_id(self) -> str:
        """Build a deterministic STIX ID for this object.
        Returns:
            The generated STIX identifier.
        """
        return pycti.Report.generate_id(name=self.name, published=self.published)
    
    def to_input_variables(self) -> dict:
        """Serialize the model into OpenCTI GraphQL payload.
        Returns:
            A dictionary matching OpenCTI input variable names.
        """
        input_variables = {
            "stix_id": self._compute_stix_id(),
            "name": self.name,
            "published": self.published.isoformat(),
            "description": self.description,
            "report_types": self.report_types,
            "objectLabel": self.labels,
            "objectMarking": self._compute_markings_ids(),
        }
        return self._keep_set_variables_only(input_variables)
