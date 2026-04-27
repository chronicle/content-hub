from __future__ import annotations
from .datamodels import *


class IronScalesParser:
    def build_incident_object(self, incident_json):
        return Incident(
            raw_data=incident_json, classification=incident_json.get("classification")
        )

    def build_impersonations(self, raw_data):
        return [
            self.build_impersonation_object(raw_json)
            for raw_json in raw_data.get("incidents", [])
        ]

    def build_impersonation_object(self, raw_json):
        return Impersonation(raw_data=raw_json)

    def build_mitigation_object(self, raw_json):
        return Mitigation(raw_data=raw_json)
