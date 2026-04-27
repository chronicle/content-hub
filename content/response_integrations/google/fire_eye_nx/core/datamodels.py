from __future__ import annotations
import copy
from TIPCommon import dict_to_flat
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo

from .FireEyeNXConstants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    FIREEYE_NX_TO_SIEM_SEVERITY,
)


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Alert:
    def __init__(
        self,
        raw_data,
        malwares=None,
        cnc_services=None,
        src=None,
        url=None,
        action=None,
        occurred=None,
        attack_time=None,
        dst=None,
        appliance_id=None,
        id=None,
        name=None,
        severity=None,
        uuid=None,
        ack=None,
        product=None,
        vlan=None,
        malicious=None,
        sc_version=None,
    ):
        self.raw_data = raw_data
        self.malwares = malwares if malwares else []
        self.cnc_services = cnc_services if cnc_services else []
        self.src = src
        self.url = url
        self.action = action
        self.occurred = occurred
        self.attack_time = attack_time
        self.dst = dst
        self.appliance_id = appliance_id
        self.id = id
        self.name = name
        self.severity = severity
        self.uuid = uuid
        self.ack = ack
        self.product = product
        self.vlan = vlan
        self.malicious = malicious
        self.sc_version = sc_version

    @property
    def priority(self):
        """
        Converts API severity format to SIEM priority
        @return: SIEM priority
        """
        return FIREEYE_NX_TO_SIEM_SEVERITY.get(self.severity, -1)

    def to_alert_info(self, environment):
        # type: (EnvironmentHandle) -> AlertInfo
        """
        Creates Siemplify Alert Info based on Indicator information
        @param environment: EnvironmentHandle object
        @return: Alert Info object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.uuid
        alert_info.display_id = self.uuid
        alert_info.name = self.name
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.priority
        alert_info.rule_generator = self.name
        alert_info.start_time = self.occurred_time_unix
        alert_info.end_time = self.occurred_time_unix
        alert_info.events = (
            [dict_to_flat(event) for event in self.create_events()]
            if self.create_events()
            else [self.to_event()]
        )
        alert_info.environment = environment.get_environment(self.raw_data)

        return alert_info

    def to_event(self):
        return dict_to_flat(self.raw_data)

    def create_events(self):
        events = []

        for malware in self.malwares:
            alert = copy.deepcopy(self.raw_data)
            alert.pop("explanation", None)
            malware["alert"] = alert
            events.append(malware)

        for service in self.cnc_services:
            alert = copy.deepcopy(self.raw_data)
            alert.pop("explanation", None)
            service["alert"] = alert
            events.append(service)

        return events

    @property
    def occurred_time_unix(self):
        return convert_string_to_unix_time(self.occurred)
