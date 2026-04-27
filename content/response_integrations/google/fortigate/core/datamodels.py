from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .UtilsManager import convert_list_to_comma_string
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAP
import copy
import uuid


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


class Policy(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        name,
        dst_items,
        src_items,
        dst_intf,
        src_intf,
        action,
        status,
    ):
        super(Policy, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.dst_items = dst_items
        self.src_items = src_items
        self.dst_intf = dst_intf
        self.src_intf = src_intf
        self.action = action
        self.status = status

    def to_table(self):
        return {
            "Name": self.name,
            "Action": self.action,
            "Status": self.status,
            "Source Interface": convert_list_to_comma_string(
                [item.get("name") for item in self.src_intf]
            ),
            "Destination Interface": convert_list_to_comma_string(
                [item.get("name") for item in self.dst_intf]
            ),
            "Source Address Count": len(self.src_items),
            "Destination Address Count": len(self.dst_items),
        }


class Entity(BaseModel):
    def __init__(self, raw_data):
        super(Entity, self).__init__(raw_data)


class AddressGroup(BaseModel):
    def __init__(self, raw_data, id, name, items, type, category, comment):
        super(AddressGroup, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.items = items
        self.type = type
        self.category = category
        self.comment = comment

    def to_table(self):
        return {
            "Name": self.name,
            "Type": self.type,
            "Category": self.category,
            "Member Count": len(self.items),
            "Comment": self.comment,
        }


class ThreatLog(BaseModel):
    def __init__(
        self, raw_data, id, msg, level, subtype, event_time, event_type, timestamp
    ):
        super(ThreatLog, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = id
        self.msg = msg
        self.level = level
        self.subtype = subtype
        self.event_time = event_time
        self.event_type = event_type
        self.timestamp = timestamp

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.msg or f"{self.subtype.upper()} Threats"
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.event_type
        alert_info.start_time = alert_info.end_time = self.timestamp
        alert_info.events = [self.as_event()]

        return alert_info

    def as_event(self):
        event_data = copy.deepcopy(self.raw_data)
        return dict_to_flat(event_data)

    def get_siemplify_severity(self):
        return SEVERITY_MAP.get(self.level, -1)
