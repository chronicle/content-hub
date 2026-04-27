from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAP
import copy
import uuid
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
        return dict_to_flat(self.raw_data)

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Alert(BaseModel):
    def __init__(self, raw_data, id, title, description, severity, type, created_date):
        super(Alert, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = id
        self.title = title
        self.description = description
        self.severity = severity
        self.type = type
        self.created_date = created_date + "Z"

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.title
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.type
        alert_info.start_time = alert_info.end_time = convert_string_to_unix_time(
            self.created_date
        )
        alert_info.events = [self.as_event()]

        return alert_info

    def as_event(self):
        event_data = copy.deepcopy(self.raw_data)
        iocs = event_data.pop("iocs", None)
        if iocs:
            for item in iocs:
                event_data[item.get("type", "")] = item.get("value", "")
        return dict_to_flat(event_data)

    def get_siemplify_severity(self):
        return SEVERITY_MAP.get(self.severity, -1)
