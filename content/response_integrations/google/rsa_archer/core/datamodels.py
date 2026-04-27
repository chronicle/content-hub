from __future__ import annotations
import uuid
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, PRIORITY_MAP
from TIPCommon import dict_to_flat
import copy
from .UtilsManager import get_list_item_by_index
from dateutil.parser import parse
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time


INCIDENT_DEVICES_KEYS = {
    "destination": "Destination_Device__Enterprise_Managemen",
    "source": "Source_Device__Enterprise_Management_Con",
}

ALERT_DEVICES_KEYS = {"destination": "Destination_Device", "source": "Source_Device"}

EVENT_DEVICES_KEYS = {
    "destination": "Destination_Device_Enterprise_Management",
    "source": "Source_Device__Enterprise_Management_Con",
}

EVENTS_TYPES_NAMES = {
    "incident": "security incident",
    "alert": "security alert",
    "event": "security event",
    "journal": "incident journals",
}

EVENTS_INFO = {
    "Incident": {
        "siemplify_event_type": "Security_Incident",
        "siemplify_event_description": "Siemplify Event based on the Security Incident. Note: in order to make it "
        "easier to map entities, you may have multiple Siemplify Events created from "
        "1 Security Incident. This is an intended behaviour.",
    },
    "Alert": {
        "siemplify_event_type": "Security_Alert",
        "siemplify_event_description": "Siemplify Event based on the Security Alert. Note: in order to make it easier"
        " to map entities, you may have multiple Siemplify Events created from 1 "
        "Security Alert. This is an intended behaviour.",
    },
    "Event": {
        "siemplify_event_type": "Security_Event",
        "siemplify_event_description": "Siemplify Event based on the Security Event. Note: in order to make it easier"
        " to map entities, you may have multiple Siemplify Events created from 1 "
        "Security Event. This is an intended behaviour.",
    },
    "Journal": {
        "siemplify_event_type": "Incident_Journal_Entry",
        "siemplify_event_description": "Siemplify Event based on the Incident Journal Entry.",
    },
}


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Reference(BaseModel):
    def __init__(self, raw_data, level_id=None, value=None, id=None):
        super(Reference, self).__init__(raw_data)
        self.level_id = level_id
        self.value = value
        self.id = id


class Application(BaseModel):
    def __init__(self, raw_data, name=None, id=None, alias=None):
        super(Application, self).__init__(raw_data)
        self.name = name
        self.id = id
        self.alias = alias


class Incident(BaseModel):
    def __init__(self, raw_data):
        super(Incident, self).__init__(raw_data)

    def to_json(self):
        self.raw_data.pop("@odata.context", None)
        return self.raw_data


class ErrorObject(BaseModel):
    def __init__(self, raw_data, description):
        super(ErrorObject, self).__init__(raw_data)
        self.description = description


class SecurityIncident(BaseModel):
    def __init__(self, raw_data, content_id=None):
        super(SecurityIncident, self).__init__(raw_data)
        self.content_id = content_id


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        name,
        priorities,
        date_created,
        incident_security_alerts_details,
        incident_security_events_details,
        incident_journals_details,
        devices_details,
        logger=None,
    ):
        super(Alert, self).__init__(raw_data)
        self.id = id
        self.uuid = str(uuid.uuid4())
        self.name = name
        self.priorities = priorities
        self.date_created = self.convert_string_to_unix_time(date_created)
        self.incident_security_alerts_details = incident_security_alerts_details
        self.incident_security_events_details = incident_security_events_details
        self.incident_journals_details = incident_journals_details
        self.devices_details = devices_details
        self.logger = logger

    def get_alert_info(self, alert_info, environment_common):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = self.uuid
        alert_info.name = self.name
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = f"RSA Archer: {self.name}"
        alert_info.start_time = self.date_created
        alert_info.end_time = self.date_created
        alert_info.events = self.create_events()

        return alert_info

    def get_siemplify_severity(self):
        return (
            max([PRIORITY_MAP.get(priority, 40) for priority in self.priorities])
            if self.priorities
            else 40
        )

    def create_events(self):
        events = self.separate_events_per_device(
            self.raw_data,
            INCIDENT_DEVICES_KEYS,
            EVENTS_INFO.get("Incident", {}),
            self.id,
            EVENTS_TYPES_NAMES.get("incident"),
        )

        if self.incident_security_alerts_details:
            self.logger.info(
                f"Found {len(self.incident_security_alerts_details)} security alerts for {self.id} security incident"
            )
            for incident_security_alert in self.incident_security_alerts_details:
                events.extend(
                    self.separate_events_per_device(
                        incident_security_alert,
                        ALERT_DEVICES_KEYS,
                        EVENTS_INFO.get("Alert", {}),
                        incident_security_alert.get("Security_Alerts_Id"),
                        EVENTS_TYPES_NAMES.get("alert"),
                    )
                ),

        if self.incident_security_events_details:
            self.logger.info(
                f"Found {len(self.incident_security_events_details)} security events for {self.id} security incident"
            )
            for incident_security_event in self.incident_security_events_details:
                events.extend(
                    self.separate_events_per_device(
                        incident_security_event,
                        EVENT_DEVICES_KEYS,
                        EVENTS_INFO.get("Event", {}),
                        incident_security_event.get("Security_Events_Id"),
                        EVENTS_TYPES_NAMES.get("event"),
                    )
                ),

        if self.incident_journals_details:
            self.logger.info(
                f"Found {len(self.incident_journals_details)} {EVENTS_TYPES_NAMES.get('journal')} for {self.id} security incident"
            )

            for incident_journal_details in self.incident_journals_details:
                incident_journal_details.update(EVENTS_INFO.get("Journal", {}))
                del incident_journal_details["@odata.context"]
                events.append(dict_to_flat(incident_journal_details))

            self.logger.info(
                f"Created {len(self.incident_journals_details)} events for {self.id} {EVENTS_TYPES_NAMES.get('journal')}"
            )

        return events

    def separate_events_per_device(
        self, raw_data, devices_keys, additional_info, item_id, item_name
    ):
        initial_data = copy.deepcopy(raw_data)
        initial_data.update(additional_info)
        del initial_data["@odata.context"]
        devices_counts = []

        for key in list(devices_keys.keys()):
            self.logger.info(
                f"Found {len(raw_data.get(devices_keys.get(key), []))} {key} devices for {item_id} {item_name}"
            )
            devices_counts.append(len(raw_data.get(devices_keys.get(key), [])))

        events_count = max(devices_counts)
        events = [] if events_count else [dict_to_flat(initial_data)]

        for i in range(events_count):
            for key in list(devices_keys.keys()):
                initial_data[devices_keys.get(key)] = self.devices_details.get(
                    get_list_item_by_index(raw_data.get(devices_keys.get(key)), i), {}
                )

            events.append(dict_to_flat(initial_data))

        self.logger.info(f"Created {len(events)} events for {item_id} {item_name}")
        return events

    def convert_string_to_unix_time(self, datetime_string):
        datetime_obj = parse(datetime_string, ignoretz=True)
        return convert_string_to_unix_time(
            datetime_obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        )


class Field(BaseModel):
    def __init__(self, raw_data, id, name, alias):
        super(Field, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.alias = alias
