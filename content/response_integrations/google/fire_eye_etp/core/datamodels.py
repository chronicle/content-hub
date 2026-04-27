from __future__ import annotations
import copy
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from .FireEyeETPConstants import ALERT_NAME
from .UtilsManager import naive_time_converted_to_aware


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        id=None,
        timestamp=None,
        severity=None,
        etp_message_id=None,
        malwares=None,
        recipients=None,
        timezone_offset=None,
    ):
        super(Alert, self).__init__(raw_data)
        self.id = id
        self.timestamp = timestamp
        self.severity = severity
        self.etp_message_id = etp_message_id
        self.malwares = malwares if malwares else []
        self.recipients = recipients if recipients else []
        self.name = ALERT_NAME
        self.timezone_offset = timezone_offset

    @property
    def priority(self):
        if self.severity == "majr":
            return 80
        elif self.severity == "crit":
            return 100

        return 60

    @property
    def events(self):
        events = []

        for malware in self.malwares:
            alert = copy.deepcopy(self.raw_data)
            alert.get("attributes", {}).get("alert", {}).get("explanation", {}).pop(
                "os_changes", None
            )
            alert.get("attributes", {}).get("alert", {}).get("explanation", {}).get(
                "malware_detected", {}
            ).pop("malware", None)
            malware["alert"] = alert
            events.append(malware)

        return events

    @property
    def recipient_events(self):
        events = []

        for recipient in self.recipients:
            event = {
                "event_name": "FireEye ETP Recipient",
                "description": "This is a custom Siemplify Event created for mapping of the recipients",
                "recipient": recipient,
            }
            events.append(event)

        return events

    @property
    def occurred_time_unix(self):
        return convert_datetime_to_unix_time(
            naive_time_converted_to_aware(self.timestamp, self.timezone_offset)
        )
