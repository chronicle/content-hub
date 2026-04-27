from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
import uuid
from .constants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    DEFAULT_ALERT_NAME,
    SEVERITY_DEFAULT_KEY,
)


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

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Alert(BaseModel):
    def __init__(self, raw_data, id, timestamp, alert_field_name):
        super(Alert, self).__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.id = id
        self.uuid = uuid.uuid4()
        self.name = self.flat_raw_data.get(alert_field_name) or DEFAULT_ALERT_NAME
        self.timestamp = timestamp
        self.events = []

    def get_alert_info(
        self,
        alert_info,
        environment_common,
        device_product_field,
        severity_field_names,
        severity_mapping_json,
    ):
        alert_info.environment = environment_common.get_environment(self.flat_raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.name
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.flat_raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity(
            severity_field_names, severity_mapping_json
        )
        alert_info.rule_generator = self.name
        alert_info.start_time = self.timestamp
        alert_info.end_time = self.timestamp
        alert_info.events = self.to_events()

        return alert_info

    def get_siemplify_severity(self, severity_field_names, severity_mapping_json):
        for key in severity_field_names:
            severity_key_value = self.flat_raw_data.get(key)

            try:
                severity_key_value = int(severity_key_value)
            except Exception:
                try:
                    severity_key_value = float(severity_key_value)
                except Exception:
                    pass

            if type(severity_key_value) == int or type(severity_key_value) == float:
                severity = severity_key_value
            else:
                severity = severity_mapping_json.get(key, {}).get(severity_key_value)

            if severity is not None:
                return severity

        return severity_mapping_json.get(SEVERITY_DEFAULT_KEY)

    def set_events(self):
        self.events = [self.to_json()]

    def to_events(self):
        return [dict_to_flat(event) for event in self.events]


class Event(BaseModel):
    def __init__(self, raw_data):
        super(Event, self).__init__(raw_data)
