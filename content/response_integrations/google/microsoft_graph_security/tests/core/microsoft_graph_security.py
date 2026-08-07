from __future__ import annotations

import dataclasses

from TIPCommon.types import SingleJson

from core.datamodels import Incident
MockProduct = object


@dataclasses.dataclass
class MicrosoftGraphSecurity(MockProduct):
    incidents: dict[str, Incident] = dataclasses.field(default_factory=dict)

    def add_incident(self, incident: Incident) -> None:
        self.incidents[incident.incident_id] = incident

    def get_incident(self, incident_id: str) -> Incident:
        return self.incidents[incident_id]

    def add_incidents(self, incidents: list[Incident]) -> None:
        self.incidents["list_incidents"] = incidents

    def list_incidents(self) -> SingleJson:
        return self.incidents["list_incidents"]
