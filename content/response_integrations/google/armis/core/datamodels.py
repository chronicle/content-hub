from __future__ import annotations
import uuid
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from typing import Dict, Optional, List

from TIPCommon import dict_to_flat, add_prefix_to_dict

from .consts import (
    ARMIS_ENRICHMENT_PREFIX,
    NOT_ASSIGNED,
    ENDPOINT_INSIGHT_TEMPLATE,
    GREEN,
    RED,
    ORANGE,
    HTML_LINK,
    INTEGRATION_NAME,
    SEVERITIES,
)
from .utils import remove_none_dictionary_values


class AlertResponse:
    def __init__(self, raw_data, data, success):
        self.raw_data = raw_data
        self.data = data
        self.success = success


class AlertResponseData:
    def __init__(
        self,
        raw_data,
        count: int = None,
        alerts: List = None,
        total: int = None,
        next=None,
        prev=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.count = count
        self.alerts = alerts
        self.total = total
        self.next = next
        self.prev = prev


class Alert:
    def __init__(
        self,
        raw_data,
        alertId: int = None,
        description: str = None,
        severity: str = None,
        status: str = None,
        title: str = None,
        type: str = None,
        deviceIds: List = None,
        time_value=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.alert_id = alertId
        self.description = description
        self.severity = severity
        self.status = status
        self.time = time_value
        self.title = title
        self.type = type
        self.device_ids = deviceIds

    def to_alert_info(self, environment, alert_events):
        alert_info = AlertInfo()
        alert_info.ticket_id = self.alert_id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.title
        alert_info.reason = self.type
        alert_info.description = self.description
        alert_info.device_vendor = INTEGRATION_NAME
        alert_info.device_product = INTEGRATION_NAME
        alert_info.priority = SEVERITIES[self.severity.upper()]
        alert_info.rule_generator = self.type
        alert_info.source_grouping_identifier = self.type
        alert_info.start_time = self.time
        alert_info.end_time = self.time
        # alert_info.environment = environment.get_environment(self.raw_data)

        return alert_info


class Activity:
    def __init__(
        self,
        raw_data,
        deviceIds: List = None,
        activityUUID: str = None,
        connectionIds: str = None,
        content: str = None,
        protocol: str = None,
        sensor=None,
        site=None,
        time_value: str = None,
        title: str = None,
        type: str = None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.device_ids = deviceIds
        self.activity_uuid = activityUUID
        self.connectionIds = connectionIds
        self.content = content
        self.protocol = protocol
        self.sensor = sensor
        self.site = site
        self.time = time_value
        self.title = title
        self.type = type

    def as_json(self, alert_type: str = "N/A", device=None):
        return {
            "alert_type": alert_type,
            "activityUUID": self.activity_uuid,
            "connectionIds": self.connectionIds,
            "content": self.content,
            "device": device.as_event() if device else "None",
            "protocol": self.protocol,
            "sensor": self.sensor,
            "site": self.site,
            "time": self.time,
            "title": self.title,
            "type": self.type,
        }

    def as_event(self, alert_type: str = "N/A", device=None):
        return dict_to_flat(self.as_json(alert_type, device))


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def as_csv(self):
        return dict_to_flat(self.as_json())

    def as_enrichment(self, prefix=ARMIS_ENRICHMENT_PREFIX):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Device(BaseModel):
    """
    Device data model
    """

    def __init__(
        self,
        raw_data: Dict,
        risk_level: Optional[int] = None,
        api_root: Optional[str] = None,
        device_id: Optional[str] = None,
        category: Optional[str] = None,
        ip_address: Optional[str] = None,
        mac_address: Optional[str] = None,
        name: Optional[str] = None,
        os: Optional[str] = None,
        os_version: Optional[str] = None,
        purdue_level: Optional[float] = None,
        tags: Optional[List[str]] = None,
        type: Optional[str] = None,
        user: Optional[str] = None,
        visibility: Optional[str] = None,
        site: Optional[dict] = None,
        site_name: Optional[str] = None,
        **kwargs,
    ):
        super(Device, self).__init__(raw_data)
        self.risk_level: int = risk_level
        self.device_id: int = device_id
        self.category: str = category
        self.ip_address: str = ip_address
        self.mac_address: str = mac_address
        self.name: str = name
        self.os: str = os
        self.os_version: str = os_version
        self.purdue_level: float = purdue_level
        self.type: str = type
        self.user: str = user
        self.tags: List[str] = tags or []
        self.visibility: str = visibility
        self.site: dict = site
        self.site_name: str = site_name

        self.report_link = (
            f"{api_root}/device/{device_id}"
            if api_root and isinstance(self.device_id, int)
            else ""
        )

    @property
    def case_wall_report_link(self):
        return self.report_link

    def as_enrichment(self, prefix=ARMIS_ENRICHMENT_PREFIX):
        enrichment_table = add_prefix_to_dict(
            dict_to_flat(
                remove_none_dictionary_values(
                    **{
                        "category": self.category,
                        "id": self.device_id,
                        "ipAddress": self.ip_address,
                        "macAddress": self.mac_address,
                        "name": self.name,
                        "os": (
                            self.os + " " + self.os_version
                            if (self.os and self.os_version)
                            else self.os or self.os_version
                        ),
                        "purdue_level": self.purdue_level,
                        "risk_level": self.risk_level,
                        "tags": ", ".join(self.tags) if self.tags else None,
                        "type": self.type,
                        "user": self.user,
                        "visibility": self.visibility,
                        "site": self.site,
                        "link": self.report_link or None,
                    }
                )
            ),
            prefix,
        )
        return enrichment_table

    def as_enrichment_csv_table(self) -> Dict:
        entity_table = dict_to_flat(
            remove_none_dictionary_values(
                **{
                    "category": self.category,
                    "id": self.device_id,
                    "ipAddress": self.ip_address,
                    "macAddress": self.mac_address,
                    "name": self.name,
                    "os": (
                        self.os + " " + self.os_version
                        if (self.os and self.os_version)
                        else self.os or self.os_version
                    ),
                    "purdue_level": self.purdue_level,
                    "risk_level": self.risk_level,
                    "tags": ", ".join(self.tags) if self.tags else None,
                    "type": self.type,
                    "user": self.user,
                    "visibility": self.visibility,
                    "site": self.site,
                    "link": self.report_link or None,
                }
            )
        )
        return [{"Key": key, "Value": value} for key, value in entity_table.items()]

    @property
    def verbal_risk_level(self) -> str:
        if isinstance(self.risk_level, int):
            if 1 <= self.risk_level <= 3:
                return "Low"
            elif 4 <= self.risk_level <= 7:
                return "Medium"
            elif 8 <= self.risk_level <= 9:
                return "High"
            else:
                return NOT_ASSIGNED
        else:
            return NOT_ASSIGNED

    @property
    def get_risk_color(self):
        if isinstance(self.risk_level, int):
            if 1 <= self.risk_level <= 3:
                return GREEN
            elif 4 <= self.risk_level <= 7:
                return ORANGE
            elif 8 <= self.risk_level <= 9:
                return RED

    def as_insight(self, entity_identifier: str) -> str:
        return ENDPOINT_INSIGHT_TEMPLATE.format(
            entity_identifier=entity_identifier,
            risk_level=self.verbal_risk_level,
            risk_color=self.get_risk_color or NOT_ASSIGNED,
            ip_address=self.ip_address,
            mac_address=self.mac_address,
            os=(
                self.os + " " + self.os_version
                if (self.os and self.os_version)
                else self.os or self.os_version or NOT_ASSIGNED
            ),
            user=self.user or NOT_ASSIGNED,
            type=self.type or NOT_ASSIGNED,
            site_name=self.site_name or NOT_ASSIGNED,
            html_report_link=HTML_LINK.format(link=self.report_link),
        )

    def as_json(self):
        return self.raw_data

    def as_event(self):
        return dict_to_flat(self.raw_data)


class DeviceAlert:
    def __init__(self, raw_data, id: int = None, **kwargs):
        self.raw_data = raw_data
        self.id = id

    def as_json(self):
        return self.raw_data

    def as_event(self):
        return dict_to_flat(self.raw_data)


class AlertConnectionResponse:
    def __init__(self, raw_data, data, success):
        self.raw_data = raw_data
        self.data = data
        self.success = success


class AlertConnectionResponseData:
    def __init__(
        self,
        raw_data,
        count: int = None,
        alert_connections: List = None,
        total: int = None,
        next=None,
        prev=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.count = count
        self.alert_connections = alert_connections
        self.total = total
        self.next = next
        self.prev = prev


class AlertConnection:
    def __init__(
        self,
        raw_data,
        id: int = None,
        title: str = None,
        protocol: str = None,
        risk: str = None,
        startTimestamp: str = None,
        endTimestamp: str = None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.id = id
        self.title = title
        self.severity = risk
        self.protocol = protocol
        self.start_time = startTimestamp
        self.end_time = endTimestamp

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return {
            "Title": self.title,
            "Protocol": self.protocol,
            "Severity": self.severity,
            "Start Time": self.start_time,
            "End Time": self.end_time,
        }
