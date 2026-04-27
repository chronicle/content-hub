from __future__ import annotations
from .datamodels import *
from .constants import (
    INCIDENT_JOURNAL_TAG,
    JOURNAL_ENTRY_TAG,
    SECURITY_INCIDENT_TAG,
    SECURITY_INCIDENTS_LEVEL_TAG,
)


class RSAArcherParser:
    def build_reference_object(self, raw_json):
        return Reference(
            raw_data=raw_json,
            level_id=raw_json.get("RequestedObject", {}).get("LevelId"),
            value=raw_json.get("RequestedObject", {})
            .get("FieldContents", {})
            .get("129", {})
            .get("Value"),
            id=raw_json.get("RequestedObject", {}).get("Id"),
        )

    def build_application_object(self, raw_json):
        app_data = raw_json[0] if raw_json else {}
        if app_data:
            return Application(
                raw_data=app_data,
                name=app_data.get("RequestedObject", {}).get("Name"),
                id=app_data.get("RequestedObject", {}).get("Id"),
                alias=app_data.get("RequestedObject", {}).get("Alias"),
            )

    def build_incident_object(self, raw_json):
        return Incident(raw_data=raw_json)

    def build_error_object(self, raw_json):
        return ErrorObject(raw_data=raw_json, description=raw_json.get("Description"))

    def build_security_incident_objects(self, raw_data):
        security_incidents = (
            [raw_data.get("Records", {}).get("Record")]
            if type(raw_data.get("Records", {}).get("Record")) is dict
            else raw_data.get("Records", {}).get("Record", [])
        )
        return [
            self.build_security_incident_object(incident)
            for incident in security_incidents
        ]

    def build_security_incident_object(self, raw_data):
        return SecurityIncident(
            raw_data=raw_data, content_id=int(raw_data.get("@contentId"))
        )

    def build_alert_object(
        self,
        incident_details,
        incident_security_alerts_details,
        incident_security_events_details,
        incident_journals_details,
        devices_details,
        siemplify_logger=None,
    ):
        return Alert(
            raw_data=incident_details,
            id=incident_details.get("Security_Incidents_Id"),
            name=incident_details.get("Title"),
            priorities=incident_details.get("Priority"),
            date_created=incident_details.get("Date_Created"),
            incident_security_alerts_details=incident_security_alerts_details,
            incident_security_events_details=incident_security_events_details,
            incident_journals_details=incident_journals_details,
            devices_details=devices_details,
            logger=siemplify_logger,
        )

    def get_devices(self, raw_data):
        devices = {}

        for device in raw_data.get("value", []):
            devices[device.get("Device_ID")] = device

        return devices

    def build_field_objects(self, raw_data):
        return [self.build_field_object(item) for item in raw_data]

    def build_field_object(self, raw_data):
        return Field(
            raw_data=raw_data,
            id=raw_data.get("RequestedObject", {}).get("Id"),
            name=raw_data.get("RequestedObject", {}).get("Name"),
            alias=raw_data.get("RequestedObject", {}).get("Alias"),
        )

    def get_application_id(self, applications):
        application_id = None

        for application in applications:
            if (
                application.get("RequestedObject", {}).get("Alias")
                == INCIDENT_JOURNAL_TAG
            ):
                application_id = application.get("RequestedObject", {}).get("Id")

        return application_id

    def get_security_incident_id(self, security_incidents):
        request_details = {
            "security_incident_id": None,
            "journal_entity_id": None,
            "level_id": None,
        }

        for security_incident in security_incidents:
            if (
                security_incident.get("RequestedObject", {}).get("Alias")
                == SECURITY_INCIDENT_TAG
            ):
                request_details["security_incident_id"] = security_incident.get(
                    "RequestedObject", {}
                ).get("Id")
            if (
                security_incident.get("RequestedObject", {}).get("Alias")
                == JOURNAL_ENTRY_TAG
            ):
                request_details["journal_entity_id"] = security_incident.get(
                    "RequestedObject", {}
                ).get("Id")
                request_details["level_id"] = security_incident.get(
                    "RequestedObject", {}
                ).get("LevelId")

        return request_details

    def get_security_incident_level(self, security_incident_levels):
        security_incident_level_id = None

        for security_incident_level in security_incident_levels:
            if (
                security_incident_level.get("RequestedObject", {}).get("Alias")
                == SECURITY_INCIDENTS_LEVEL_TAG
            ):
                security_incident_level_id = security_incident_level.get(
                    "RequestedObject", {}
                ).get("Id")

        return security_incident_level_id
