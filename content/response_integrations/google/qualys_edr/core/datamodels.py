from __future__ import annotations
from TIPCommon import dict_to_flat
import uuid
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAP
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())


class Alert(BaseModel):
    def __init__(self, raw_data, id, type, score, datetime):
        super(Alert, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = id
        self.name = f"Suspicious: {type}"
        self.type = type
        self.score = int(score) if score or score == 0 else None
        self.datetime = convert_string_to_unix_time(datetime)
        self.events = []

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.name
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.type
        alert_info.start_time = self.datetime
        alert_info.end_time = self.datetime
        alert_info.events = self.to_events()

        return alert_info

    def get_siemplify_severity(self):
        if not self.score:
            return SEVERITY_MAP["INFO"]

        if 3 <= self.score <= 4:
            return self.score["LOW"]
        elif 5 <= self.score <= 6:
            return SEVERITY_MAP["MEDIUM"]
        elif 7 <= self.score <= 8:
            return SEVERITY_MAP["HIGH"]
        elif 9 <= self.score <= 10:
            return SEVERITY_MAP["CRITICAL"]

        return SEVERITY_MAP["INFO"]

    def set_events(self):
        self.events = [self.raw_data]

    def to_events(self):
        return [dict_to_flat(event) for event in self.events]
