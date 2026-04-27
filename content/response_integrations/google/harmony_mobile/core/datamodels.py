from __future__ import annotations
import copy
import uuid
from datetime import datetime
from TIPCommon import dict_to_flat, add_prefix_to_dict
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from .constants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    SEVERITY_MAP,
    DEVICE_RISK_MAP,
    DEVICE_STATUS_MAP,
    DEVICE_RISK_COLOR_MAP,
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
    def __init__(self, raw_data, id, threat_factors, details, severity, timestamp):
        super(Alert, self).__init__(raw_data)
        self.id = id
        self.uuid = uuid.uuid4()
        self.threat_factors = threat_factors
        self.details = details
        self.severity = severity
        self.timestamp = convert_datetime_to_unix_time(
            datetime.strptime(timestamp, "%m/%d/%Y %H:%M:%S")
        )
        self.events = []

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.threat_factors
        alert_info.description = self.details
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.threat_factors
        alert_info.start_time = self.timestamp
        alert_info.end_time = self.timestamp
        alert_info.events = self.to_events()

        return alert_info

    def get_siemplify_severity(self):
        return SEVERITY_MAP.get(self.severity, -1)

    def set_events(self):
        self.events = [self.to_json()]

    def to_events(self):
        return [dict_to_flat(event) for event in self.events]


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        client_version,
        device_type,
        email,
        last_connection,
        model,
        name,
        number,
        os_type,
        os_version,
        risk,
        status,
    ):
        super(Device, self).__init__(raw_data)
        self.raw_data = raw_data
        self.client_version = client_version
        self.device_type = device_type
        self.email = email
        self.last_connection = last_connection
        self.model = model
        self.name = name
        self.number = number
        self.os_type = os_type
        self.os_version = os_version
        self.risk = DEVICE_RISK_MAP.get(risk, "Unknown")
        self.status = DEVICE_STATUS_MAP.get(status, "Unknown")

    def to_json(self):
        json_data = copy.deepcopy(self.raw_data)
        json_data["risk"] = self.risk
        json_data["status"] = self.status
        return json_data

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(
            {
                "client_version": self.client_version,
                "device_type": self.device_type,
                "email": self.email,
                "last_connection": self.last_connection,
                "model": self.model,
                "name": self.name,
                "number": self.number,
                "os_type": self.os_type,
                "os_version": self.os_version,
                "risk": self.risk,
                "status": self.status,
            }
        )

        data = {key: value for key, value in data.items() if value is not None}
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_table(self):
        return self.to_enrichment_data()

    def as_insight(self):
        return (
            f"<table>"
            f"<tbody>"
            f"<tr>"
            f"<td>"
            f'<h2 style="text-align: left;">'
            f"<strong>Risk Level: "
            f'<span style="color: {DEVICE_RISK_COLOR_MAP.get(self.risk)};">\
            {self.risk}</span>'
            f"</strong>"
            f"</h2>"
            f"</td>"
            f"<td>"
            f'<h2 style="text-align: left;">'
            f"<strong>&nbsp;Status: {self.status}</strong>"
            f"</h2>"
            f"</td>"
            f"</tr>"
            f"</tbody>"
            f"</table>"
            f"<p>"
            f"<strong>Device: </strong>{self.device_type}"
            f"<strong><br />OS Type: </strong>{self.os_type}"
            f"<strong><br />OS Version: </strong>{self.os_version}"
            f"<strong><br />Email: </strong>{self.email}"
            f"<strong><br />Model: </strong>{self.model}"
            f"<strong><br />Number: </strong>{self.number}"
            f"</p>"
        )
