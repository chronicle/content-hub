from __future__ import annotations
import copy
from TIPCommon import dict_to_flat, add_prefix_to_dict
import uuid
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAP, DEFAULT_SEVERITY
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

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        alert_id,
        type,
        source,
        severity,
        start_time,
        end_time,
        create_time,
        messages,
    ):
        super(Alert, self).__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.uuid = uuid.uuid4()
        self.id = alert_id
        self.type = type
        self.source = source
        self.severity = severity
        self.start_time = start_time
        self.end_time = end_time
        self.create_time = convert_string_to_unix_time(create_time)
        self.messages = messages
        self.events = []

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.flat_raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.type
        alert_info.description = self.source
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.flat_raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = (
            SEVERITY_MAP.get(self.severity.lower(), DEFAULT_SEVERITY)
            if self.severity is not None
            else DEFAULT_SEVERITY
        )
        alert_info.rule_generator = self.type
        alert_info.start_time = convert_string_to_unix_time(self.start_time)
        alert_info.end_time = (
            convert_string_to_unix_time(self.end_time)
            if self.end_time
            else self.create_time
        )
        alert_info.events = self.to_events()

        return alert_info

    def set_events(self):
        self.events = []

    def to_events(self):
        original_event = copy.deepcopy(self.to_json())
        original_event.get("data", {}).pop("messages", None)

        return (
            [
                {**dict_to_flat(original_event), **dict_to_flat(message)}
                for message in self.messages
            ]
            if self.messages
            else [dict_to_flat(original_event)]
        )
