from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
import copy
import uuid
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAP, RULE_GENERATOR


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


class Asset(BaseModel):
    def __init__(self, raw_data, id, ip):
        super(Asset, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = id
        self.ip = ip
        self.vulnerabilities = []

    def get_alert_info(
        self, alert_info, environment_common, device_product_field, execution_time
    ):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.vulnerabilities[0].raw_data)
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = f"{self.ip}: New Vulnerabilities"
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_highest_severity()
        alert_info.rule_generator = RULE_GENERATOR
        alert_info.start_time = alert_info.end_time = execution_time
        alert_info.events = [
            vulnerability.as_event() for vulnerability in self.vulnerabilities
        ]

        return alert_info

    def get_highest_severity(self):
        return max(
            [
                SEVERITY_MAP.get(vuln.details.severity, -1)
                for vuln in self.vulnerabilities
            ]
        )


class Vulnerability(BaseModel):
    def __init__(self, raw_data, id, since):
        super(Vulnerability, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = id
        self.since = since
        self.details = None

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.details.title
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = RULE_GENERATOR
        alert_info.start_time = alert_info.end_time = convert_string_to_unix_time(
            self.since
        )
        alert_info.events = [self.as_event()]

        return alert_info

    def as_event(self):
        event_data = copy.deepcopy(self.raw_data)
        event_data.update(self.details.to_json())
        event_data.pop("links", None)
        return dict_to_flat(event_data)

    def get_siemplify_severity(self):
        return SEVERITY_MAP.get(self.details.severity, -1)


class VulnerabilityDetails(BaseModel):
    def __init__(self, raw_data, id, title, severity):
        super(VulnerabilityDetails, self).__init__(raw_data)
        self.id = id
        self.title = title
        self.severity = severity
