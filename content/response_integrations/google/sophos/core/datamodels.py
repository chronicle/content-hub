from __future__ import annotations
import uuid
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAP, HEALTH_COLOR_MAP
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from .utils import convert_list_to_comma_string


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Alert(BaseModel):
    def __init__(self, raw_data, id, threat, description, severity, alert_type, when):
        super(Alert, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = id
        self.threat = threat
        self.severity = severity
        self.description = description
        self.alert_type = alert_type
        self.when = when

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.threat or self.alert_type
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.alert_type
        alert_info.start_time = convert_string_to_unix_time(self.when)
        alert_info.end_time = convert_string_to_unix_time(self.when)
        alert_info.events = [self.as_event()]

        return alert_info

    def get_siemplify_severity(self):
        return SEVERITY_MAP.get(self.severity, -1)

    def as_event(self):
        return dict_to_flat(self.raw_data)


class Api_Root(BaseModel):
    def __init__(self, raw_data, id, api_root):
        super(Api_Root, self).__init__(raw_data)
        self.id = id
        self.api_root = api_root


class Endpoint(BaseModel):
    def __init__(
        self,
        raw_data,
        hostname=None,
        ip_address=None,
        scan_id=None,
        service_info=None,
        service_details=None,
        health=None,
        threat_status=None,
        services_status=None,
        type=None,
        os_name=None,
        os_build=None,
        mac_address=None,
        associated_person=None,
        is_server=None,
        last_seen_at=None,
        is_isolated=None,
    ):
        super(Endpoint, self).__init__(raw_data)
        self.hostname = hostname
        self.ip_address = ip_address
        self.scan_id = scan_id
        self.service_info = service_info
        self.service_details = service_details
        self.health = health
        self.threat_status = threat_status
        self.services_status = services_status
        self.type = type
        self.os_name = os_name
        self.os_build = os_build
        self.mac_address = mac_address
        self.associated_person = associated_person
        self.is_server = is_server
        self.last_seen_at = last_seen_at
        self.is_isolated = is_isolated

    def to_json(self):
        return {"services": self.service_info}

    def to_enrichment_json(self):
        return self.raw_data

    def to_csv(self):
        table_data = self.to_table()
        return dict_to_flat(table_data)

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_table(self):
        return {
            "health": self.health,
            "threat_status": self.threat_status,
            "services_status": self.services_status,
            "type": self.type,
            "hostname": self.hostname,
            "os": self.os_name,
            "os_build": self.os_build,
            "ipv4": convert_list_to_comma_string(self.ip_address),
            "mac_address": convert_list_to_comma_string(self.mac_address),
            "associated_person": self.associated_person,
            "is_server": self.is_server,
            "last_seen": self.last_seen_at,
            "isolated": self.is_isolated,
        }

    def to_insight(self):
        health_color = HEALTH_COLOR_MAP.get(self.health.title(), "#000000")
        return (
            '<h3><strong>Health: <span style="color: {health_color};">{health}</span></strong></h3>'
            "<p><strong>Isolated: </strong>{is_isolated}<strong><br />"
            "Hostname: </strong>{hostname}<br />"
            "<strong>IP Address: </strong>{ip_address}<br />"
            "<strong>Type: </strong>{type}<strong><br />"
            "OS: </strong>{os_name} Build: {os_build}<strong><br />"
            "Server: </strong>{is_server}<strong><br />"
            "</strong><strong>Associated Person: </strong>{associated_person}<br />"
            "<strong>Last Seen: </strong>{last_seen}</p><p>&nbsp;</p>".format(
                health_color=health_color,
                health=self.health.title(),
                is_isolated=self.is_isolated,
                hostname=self.hostname,
                ip_address=convert_list_to_comma_string(self.ip_address),
                type=self.type,
                os_name=self.os_name,
                os_build=self.os_build,
                is_server=self.is_server,
                associated_person=self.associated_person,
                last_seen=self.last_seen_at,
            )
        )


class ServiceDetails(BaseModel):
    def __init__(self, raw_data, status=None, name=None):
        super(ServiceDetails, self).__init__(raw_data)
        self.status = status
        self.name = name

    def to_csv(self):
        return {
            "Name": self.name,
            "Status": self.status.upper() if self.status else None,
        }


class Events(BaseModel):
    def __init__(
        self,
        raw_data,
        name=None,
        type=None,
        source=None,
        threat=None,
        severity=None,
        timestamp=None,
    ):
        super(Events, self).__init__(raw_data)
        self.name = name
        self.type = type
        self.source = source
        self.threat = threat
        self.severity = severity
        self.timestamp = timestamp

    def to_csv(self):
        return {
            "Name": self.name,
            "Type": self.type,
            "Source": self.source,
            "Threat": self.threat,
            "Severity": self.severity,
            "Timestamp": self.timestamp,
        }


class FileHash(BaseModel):
    def __init__(
        self, raw_data, type=None, comment=None, created_at=None, hash_value=None
    ):
        super(FileHash, self).__init__(raw_data)
        self.type = type
        self.comment = comment
        self.created_at = created_at
        self.hash_value = hash_value

    def to_csv(self):
        table_data = self.to_table()
        return dict_to_flat(table_data)

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_table(self):
        return {
            "type": self.type,
            "comment": self.comment,
            "createdAt": self.created_at,
        }

    def to_insight(self):
        return (
            '<h3>Status: <span style="color: #ff0000;">Blocked</span></h3><p>'
            "<strong>Comment: </strong>"
            "{comment}<br />"
            "<strong>Created At: </strong>{created_at}</p>".format(
                comment=self.comment, created_at=self.created_at
            )
        )
