from __future__ import annotations
from TIPCommon import dict_to_flat, add_prefix_to_dict
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from .NozomiNetworksConstants import DEVICE_VENDOR, DEVICE_PRODUCT


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Vulnerability(BaseModel):
    def __init__(
        self,
        raw_data,
        node_id,
        cve,
        cwe_name,
        cve_summary,
        cve_score,
        zone,
        resolved,
        cve_references,
        cve_creation_time,
        cve_update_time,
    ):
        super(Vulnerability, self).__init__(raw_data)
        self.node_id = node_id
        self.cve = cve
        self.cwe_name = cwe_name
        self.cve_summary = cve_summary
        self.cve_score = cve_score
        self.zone = zone
        self.resolved = resolved
        self.cve_references = cve_references
        self.cve_creation_time = cve_creation_time
        self.cve_update_time = cve_update_time

    def to_csv(self):
        return {
            "Ip address": self.node_id,
            "CVE ID": self.cve,
            "Vulnerability name": self.cwe_name,
            "Vulnerability Description": self.cve_summary,
            "CVE Score": self.cve_score,
            "Zone": self.zone,
            "Is Resolved": self.resolved,
            "References": self.cve_references,
            "CVE Creation Time": self.cve_creation_time,
            "CVE Update Time": self.cve_update_time,
        }


class QueryResult(BaseModel):
    def __init__(self, raw_data):
        super(QueryResult, self).__init__(raw_data)


class Alert(BaseModel):
    def __init__(
        self, raw_data, id, description, type_name, name, severity, created_time
    ):
        super(Alert, self).__init__(raw_data)
        self.id = id
        self.description = description
        self.type_name = type_name
        self.name = name
        self.severity = severity
        self.created_time = created_time

    @property
    def priority(self):
        """
        Converts API severity format to SIEM priority
        @return: SIEM priority
        """
        if self.severity >= 10:
            return 100
        elif self.severity >= 8:
            return 80
        elif self.severity >= 6:
            return 60
        elif self.severity >= 4:
            return 40
        else:
            return -1

    def to_alert_info(self, environment):
        # type: (EnvironmentHandle) -> AlertInfo
        """
        Creates Siemplify Alert Info based on Indicator information
        @param environment: EnvironmentHandle object
        @return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.id
        alert_info.display_id = self.id
        alert_info.name = f"Nozomi alert: {self.name}"
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.priority
        alert_info.rule_generator = self.type_name
        alert_info.start_time = self.created_time
        alert_info.end_time = self.created_time
        alert_info.events = [self.to_event()]
        alert_info.environment = environment.get_environment(self.raw_data)

        return alert_info

    def to_event(self):
        return dict_to_flat(self.raw_data)


class Node(BaseModel):
    def __init__(
        self,
        raw_data,
        level,
        appliance_host,
        ip,
        mac_address,
        vlan_id,
        os,
        roles,
        vendor,
        firmware_version,
        serial_number,
        product_name,
        type,
        protocols,
        device_id,
        capture_device,
        is_broadcast,
        is_public,
        is_confirmed,
        is_disabled,
        is_licensed,
        last_activity_time,
    ):
        super(Node, self).__init__(raw_data)
        self.level = level
        self.appliance_host = appliance_host
        self.ip = ip
        self.mac_address = mac_address
        self.vlan_id = vlan_id
        self.os = os
        self.roles = roles
        self.vendor = vendor
        self.firmware_version = firmware_version
        self.serial_number = serial_number
        self.product_name = product_name
        self.type = type
        self.protocols = protocols
        self.device_id = device_id
        self.capture_device = capture_device
        self.is_broadcast = is_broadcast
        self.is_public = is_public
        self.is_confirmed = is_confirmed
        self.is_disabled = is_disabled
        self.is_licensed = is_licensed
        self.last_activity_time = last_activity_time

    def to_enrichment_data(self, additional_fields=None, prefix=None):
        data = {
            "level": self.level,
            "appliance_host": self.appliance_host,
            "ip": self.ip,
            "mac_address": self.mac_address,
            "vlan_id": self.vlan_id,
            "os": self.os,
            "roles": self.roles,
            "vendor": self.vendor,
            "firmware_version": self.firmware_version,
            "serial_number": self.serial_number,
            "product_name": self.product_name,
            "type": self.type,
            "protocols": self.protocols,
            "device_id": self.device_id,
            "capture_device": self.capture_device,
            "is_broadcast": self.is_broadcast,
            "is_public": self.is_public,
            "is_confirmed": self.is_confirmed,
            "is_disabled": self.is_disabled,
            "is_licensed": self.is_licensed,
        }
        for field in additional_fields:
            if self.raw_data.get(field):
                data[field] = self.raw_data.get(field)
        return (
            add_prefix_to_dict(dict_to_flat(data), prefix)
            if prefix
            else dict_to_flat(data)
        )
