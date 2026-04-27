from __future__ import annotations
from .datamodels import *


class FortiSIEMParser:
    def build_alert_objects(self, raw_data):
        return [self.build_alert_object(item) for item in raw_data.get("data", [])]

    @staticmethod
    def build_alert_object(raw_data):
        return Alert(
            raw_data=raw_data,
            incident_id=raw_data.get("incidentId"),
            incident_title=raw_data.get("incidentTitle"),
            event_severity=raw_data.get("eventSeverity"),
            event_type=raw_data.get("eventType"),
            incident_first_seen=raw_data.get("incidentFirstSeen"),
            incident_last_seen=raw_data.get("incidentLastSeen"),
            attack_technique=raw_data.get("attackTechnique"),
            ph_incident_category=raw_data.get("phIncidentCategory"),
            incident_target=raw_data.get("incidentTarget"),
            incident_status=raw_data.get("incidentStatus"),
            customer=raw_data.get("customer"),
        )

    def build_event_objects(self, raw_data):
        return [self.build_event_object(item) for item in raw_data]

    @staticmethod
    def build_event_object(raw_data):
        return Event(raw_data=raw_data, event_id=raw_data.get("id"))

    @staticmethod
    def build_device_info_object(raw_data):
        return DeviceInfo(raw_data=raw_data)

    def build_query_result_objects(self, raw_data):
        events = raw_data.get("queryResult", {}).get("events", {})
        if events is None:
            return None
        events = events.get("event")
        events = [events] if isinstance(events, dict) else events
        return [self.build_event_object(event) for event in events]
