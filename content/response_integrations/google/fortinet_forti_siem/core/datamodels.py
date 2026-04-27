from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
import uuid
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAP


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
        incident_id,
        incident_title,
        event_severity,
        event_type,
        incident_first_seen,
        incident_last_seen,
        attack_technique,
        ph_incident_category,
        incident_target,
        incident_status,
        customer,
    ):
        super(Alert, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.incident_id = str(incident_id)
        self.incident_title = incident_title
        self.event_severity = event_severity
        self.event_type = event_type
        self.incident_first_seen = incident_first_seen
        self.incident_last_seen = incident_last_seen
        self.attack_technique = attack_technique
        self.ph_incident_category = ph_incident_category
        self.incident_target = incident_target
        self.incident_status = incident_status
        self.customer = customer
        self.events = []

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.incident_id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.incident_title
        alert_info.description = self.incident_title
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.event_type
        alert_info.source_grouping_identifier = self.incident_id
        alert_info.start_time = self.incident_first_seen
        alert_info.end_time = self.incident_last_seen
        alert_info.extensions.update(
            {
                "attackTechnique": self.attack_technique,
                "phIncidentCategory": self.ph_incident_category,
                "incidentTarget": self.incident_target,
                "incidentStatus": self.incident_status,
                "customer": self.customer,
            }
        )
        alert_info.events = self.to_events()

        return alert_info

    def get_siemplify_severity(self):
        severity = self.event_severity * 10

        if 0 <= severity <= SEVERITY_MAP["LOW"]:
            return SEVERITY_MAP["LOW"]
        elif SEVERITY_MAP["LOW"] < severity <= SEVERITY_MAP["MEDIUM"]:
            return SEVERITY_MAP["MEDIUM"]
        elif SEVERITY_MAP["MEDIUM"] < severity <= SEVERITY_MAP["HIGH"]:
            return SEVERITY_MAP["HIGH"]
        elif SEVERITY_MAP["HIGH"] < severity <= SEVERITY_MAP["CRITICAL"]:
            return SEVERITY_MAP["CRITICAL"]

        return SEVERITY_MAP["INFO"]

    def set_events(self, events, existing_event_ids, events_limit):
        for event in events:
            if len(self.events) >= events_limit:
                break

            if event.event_id not in existing_event_ids:
                event.raw_data["device_product"] = DEVICE_PRODUCT
                self.events.append(event)

    def to_events(self):
        return [dict_to_flat(event.raw_data) for event in self.events]


class Event(BaseModel):
    def __init__(self, raw_data, event_id):
        super(Event, self).__init__(raw_data)
        self.raw_data = raw_data
        self.event_id = str(event_id)

    def to_table(self):
        json_results = {}
        for key, value in self.raw_data.items():
            if key == "attributes":
                for attribute in value.get("attribute"):
                    json_results.update(
                        {attribute.get("@name"): attribute.get("#text")}
                    )
            else:
                json_results.update({key: value})
        return json_results

    def to_json(self):
        json_results = {}
        attributes_json = {}

        for key, value in self.raw_data.items():
            if key == "attributes":
                for attribute in value.get("attribute"):
                    attributes_json.update(
                        {attribute.get("@name"): attribute.get("#text")}
                    )
            else:
                json_results.update({key: value})

            json_results.update({"attributes": attributes_json})
        return json_results


class DeviceInfo(BaseModel):
    def __init__(self, raw_data):
        super(DeviceInfo, self).__init__(raw_data)

    def to_enrichment_data(self, prefix=None):
        device = self.raw_data.get("device", {})
        data = {
            "accessIp": device.get("accessIp"),
            "name": device.get("name"),
            "creationMethod": device.get("creationMethod"),
            "deviceType_model": device.get("deviceType", {}).get("model"),
            "deviceType_accessProtocols": device.get("deviceType", {}).get(
                "accessProtocols"
            ),
            "deviceType_vendor": device.get("deviceType", {}).get("vendor"),
            "discoverMethod": device.get("discoverMethod"),
            "discoverTime": device.get("discoverTime"),
        }

        data = dict_to_flat({key: value for key, value in data.items() if value})
        return add_prefix_to_dict(data, prefix) if prefix else data
