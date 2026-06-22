import pycti
from core.datamodels.base_octi_object import BaseOCTIObject


class Grouping(BaseOCTIObject):
    name: str
    context: str
    description: str | None = None
    labels: list[str] | None = None
    markings: list[str] | None = None

    def _compute_stix_id(self) -> str:
        return pycti.Grouping.generate_id(name=self.name, context=self.context)

    def to_input_variables(self) -> dict:
        input_variables = {
            "stix_id": self._compute_stix_id(),
            "name": self.name,
            "context": self.context,
            "description": self.description,
            "objectLabel": self.labels,
            "objectMarking": self._compute_markings_ids(),
        }
        return self._keep_set_variables_only(input_variables)
