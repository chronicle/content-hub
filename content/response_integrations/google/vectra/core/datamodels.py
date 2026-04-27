from __future__ import annotations
import copy
import uuid

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon import dict_to_flat, add_prefix_to_dict, flat_dict_to_csv
from .constants import DEFAULT_DEVICE_VENDOR, DEFAULT_DEVICE_PRODUCT


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Endpoint(BaseModel):
    def __init__(
        self,
        raw_data,
        endpoint_id,
        name,
        state,
        threat,
        certainty,
        ip,
        tags,
        note,
        url,
        last_modified,
        groups,
        is_key_asset,
        has_active_traffic,
        is_targeting_key_asset,
        privilege_level,
        previous_ip,
    ):
        super(Endpoint, self).__init__(raw_data)
        self.endpoint_id = endpoint_id
        self.name = name
        self.state = state
        self.threat = threat
        self.certainty = certainty
        self.ip = ip
        self.tags = tags
        self.note = note
        self.url = url
        self.last_modified = last_modified
        self.groups = groups
        self.is_key_asset = is_key_asset
        self.has_active_traffic = has_active_traffic
        self.is_targeting_key_asset = is_targeting_key_asset
        self.privilege_level = privilege_level
        self.previous_ip = previous_ip

    def to_csv(self):
        return flat_dict_to_csv(
            {
                "id": self.endpoint_id,
                "name": self.name,
                "state": self.state,
                "threat": self.threat,
                "certainty": self.certainty,
                "ip": self.ip,
                "tags": f'{" ".join([tag for tag in self.tags])}',
                "note": self.note,
                "url": self.url,
                "last_modified": self.last_modified,
                "groups": f'{" ".join([tag["name"] for tag in self.groups])}',
                "is_key_asset": self.is_key_asset,
                "has_active_traffic": self.has_active_traffic,
                "is_targeting_key_asset": self.is_targeting_key_asset,
                "privilege_level": self.privilege_level,
                "previous_ip": f'{" ".join([tag for tag in self.previous_ip])}',
            }
        )

    def to_enrichment_data(self, prefix=None):
        new_dict = {
            "id": self.endpoint_id,
            "name": self.name,
            "state": self.state,
            "threat": self.threat,
            "certainty": self.certainty,
            "ip": self.ip,
            "tags": f'{" ".join([tag for tag in self.tags])}',
            "note": self.note,
            "url": self.url,
            "last_modified": self.last_modified,
            "groups": f'{" ".join([tag["name"] for tag in self.groups])}',
            "is_key_asset": self.is_key_asset,
            "has_active_traffic": self.has_active_traffic,
            "is_targeting_key_asset": self.is_targeting_key_asset,
            "privilege_level": self.privilege_level,
            "previous_ip": f'{" ".join([tag for tag in self.previous_ip])}',
        }
        data = dict_to_flat(new_dict)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Detection(BaseModel):
    def __init__(
        self,
        raw_data,
        detection_id,
        name,
        tags,
        sensor_name,
        priority,
        category,
        first_timestamp,
        last_timestamp,
        grouped_details,
        detection_category,
        detection_type,
        certainty,
        threat,
    ):
        super(Detection, self).__init__(raw_data)
        self.detection_id = detection_id
        self.uuid = str(uuid.uuid4())
        self.name = name
        self.tags = tags
        self.sensor_name = sensor_name
        self.priority = self.get_siemplify_priority(priority)
        self.category = category
        self.first_timestamp = convert_string_to_unix_time(first_timestamp)
        self.last_timestamp = convert_string_to_unix_time(last_timestamp)
        self.timestamp = self.last_timestamp
        self.grouped_details = grouped_details
        self.detection_category = detection_category
        self.detection_type = detection_type
        self.certainty = certainty
        self.threat = threat

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.detection_id
        alert_info.display_id = self.uuid
        alert_info.name = self.detection_type
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.priority = self.priority
        alert_info.rule_generator = self.detection_category
        alert_info.start_time = self.first_timestamp
        alert_info.end_time = self.last_timestamp
        alert_info.events = [dict_to_flat(detail) for detail in self.create_events()]
        alert_info.extensions = dict_to_flat(
            {"certainty": self.certainty, "threat": self.threat}
        )
        alert_info.device_product = (
            alert_info.events[0].get(device_product_field) or DEFAULT_DEVICE_PRODUCT
        )

        return alert_info

    def get_siemplify_priority(self, priority):
        result = 40
        if priority > 40:
            result = 60
        if priority > 60:
            result = 80

        if priority > 80:
            result = 100

        return result

    def create_events(self):
        detection_data = copy.deepcopy(self.raw_data)
        detection_data.pop("grouped_details", None)
        for detail in self.grouped_details:
            detail["detection"] = detection_data
        return self.grouped_details


class TriageRule(BaseModel):
    def __init__(
        self,
        raw_data,
        triage_id,
        enabled,
        detection_category,
        triage_category,
        detection,
        whitelist,
        priority,
        created_at,
        description,
    ):
        super(TriageRule, self).__init__(raw_data)
        self.triage_id = triage_id
        self.enabled = enabled
        self.detection_category = detection_category
        self.triage_category = triage_category
        self.detection = detection
        self.whitelist = whitelist
        self.priority = priority
        self.created_at = created_at
        self.description = description

    def to_csv(self):
        return {
            "ID": self.triage_id,
            "Enabled": self.enabled,
            "Detection Category": self.detection_category,
            "Triage Category": self.triage_category,
            "Detection ": self.detection,
            "Whitelist": self.whitelist,
            "Priority": self.priority,
            "Created At": self.created_at,
        }
