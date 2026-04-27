from __future__ import annotations
from .datamodels import Incident
from .constants import SIEM_TO_SYMANTEC_PRIORITY


class SymantecATPParser:
    @staticmethod
    def build_incident(incident_data):
        return Incident(incident_data, **incident_data)

    @staticmethod
    def convert_siem_priorities_to_symantec(priorities):
        return [
            SIEM_TO_SYMANTEC_PRIORITY.get(priority.upper()) for priority in priorities
        ]
