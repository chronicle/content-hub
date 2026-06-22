import pycti
from core.datamodels.base_octi_object import BaseOCTIObject


class Tool(BaseOCTIObject):
    name: str
    description: str | None = None
    tool_types: list[str] | None = None
    labels: list[str] | None = None
    markings: list[str] | None = None

    def _compute_stix_id(self) -> str:
        return pycti.Tool.generate_id(name=self.name)

    def to_input_variables(self) -> dict:
        input_variables = {
            "stix_id": self._compute_stix_id(),
            "name": self.name,
            "description": self.description,
            "tool_types": self.tool_types,
            "objectLabel": self.labels,
            "objectMarking": self._compute_markings_ids(),
        }
        return self._keep_set_variables_only(input_variables)
