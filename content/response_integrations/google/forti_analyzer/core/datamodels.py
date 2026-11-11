from __future__ import annotations
import copy
from TIPCommon import dict_to_flat, add_prefix_to_dict
from forti_analyzer.core.constants import (
    INTEGRATION_PREFIX,
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    SIEMPLIFY_SEVERITY_MAPPING,
)
from forti_analyzer.core.UtilsManager import seconds_to_milliseconds, convert_string_to_json
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from EnvironmentCommon import EnvironmentHandle
from typing import List, Dict


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


class Log(BaseModel):
    def __init__(self, raw_data, log_id) -> None:
        super(Log, self).__init__(raw_data)
        self.raw_data = raw_data
        self.log_id = str(log_id)


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        adm_user,
        build,
        ip_address,
        last_checked,
        last_resync,
        name,
        sn,
        os_type,
        os_ver,
        patch,
        platform_str,
        version,
        desc,
    ):
        super().__init__(raw_data)
        self.adm_user = adm_user
        self.build = build
        self.ip_address = ip_address
        self.last_checked = last_checked
        self.last_resync = last_resync
        self.name = name
        self.sn = sn
        self.os_type = os_type
        self.os_ver = os_ver
        self.patch = patch
        self.platform_str = platform_str
        self.version = version
        self.desc = desc

    def to_table(self):
        table_data = {
            "adm_user": self.adm_user,
            "build": self.build,
            "ip": self.ip_address,
            "last_checked": self.last_checked,
            "last_resync": self.last_resync,
            "name": self.name,
            "sn": self.sn,
            "os_type": self.os_type,
            "os_ver": self.os_ver,
            "patch": self.patch,
            "platform_str": self.platform_str,
            "version": self.version,
            "desc": self.desc,
        }
        return {key: value for key, value in table_data.items() if value is not None}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        adom,
        alert_id,
        alert_time,
        subject,
        severity,
        trigger_name,
        first_log_time,
        last_log_time,
    ):
        super().__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.adom = adom
        self.alert_id = alert_id
        self.alert_time = seconds_to_milliseconds(alert_time)
        self.subject = subject
        self.severity = severity
        self.trigger_name = trigger_name
        self.first_log_time = seconds_to_milliseconds(first_log_time)
        self.last_log_time = seconds_to_milliseconds(last_log_time)
        self.events = []

    def get_alert_info(
        self,
        alert_info: AlertInfo,
        environment_common: EnvironmentHandle,
        device_product_field: str,
    ) -> AlertInfo:
        """
        Build AlertInfo object
        Args:
            alert_info (AlertInfo): AlertInfo object
            environment_common (EnvironmentHandle): environment common for fetching the environment
            device_product_field (str): key to use to fetch device product value

        Returns:
            (AlertInfo): AlertInfo object
        """
        alert_info.environment = environment_common.get_environment(self.flat_raw_data)
        alert_info.ticket_id = self.alert_id
        alert_info.display_id = f"{INTEGRATION_PREFIX}_{self.alert_id}"
        alert_info.name = self.subject
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.flat_raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.trigger_name
        alert_info.source_grouping_identifier = self.trigger_name
        alert_info.start_time = self.first_log_time
        alert_info.end_time = self.last_log_time
        alert_info.events = self.to_events()

        return alert_info

    def get_siemplify_severity(self) -> int:
        """
        Get siemplify severity from alert severity
        Args:

        Returns:
            (int): siemplify severity
        """
        return SIEMPLIFY_SEVERITY_MAPPING.get(self.severity, -1)

    def set_events(self, alert_details: Dict, logs: List) -> None:
        """
        Set Alert events
        Args:
            alert_details (dict): alert details to use for event
            logs (list): list of logs to use for events

        Returns:
           (): None
        """
        event_data = copy.deepcopy(self.raw_data)
        event_data["siemplify_type"] = "Alert"
        event_data["additional_info"] = alert_details[0] if alert_details else {}
        event_data["extrainfo"] = (
            convert_string_to_json(self.raw_data.get("extrainfo"))
            if self.raw_data.get("extrainfo")
            else {}
        )
        self.events.append(event_data)

        for log in logs:
            log["siemplify_type"] = "Log"
            self.events.append(log)

    def to_events(self):
        """
        Convert Alert events to siemplify events
        Args:

        Returns:
           (list): list of flat events
        """
        return [dict_to_flat(event) for event in self.events]


class AlertCommentResponse(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
