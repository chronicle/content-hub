from __future__ import annotations
from .constants import DEFAULT_DELIMITER, DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAPPING
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from typing import Union, List
from EnvironmentCommon import (
    EnvironmentHandleForFileSystem,
    EnvironmentHandleForDBSystem,
)
from TIPCommon import dict_to_flat
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
import copy


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Investigation(BaseModel):
    def __init__(
        self,
        raw_data: dict,
        title: str,
        status: str,
        source: str,
        assignee_email: str,
        alert_types: list,
        created_time: str,
        rrn: str,
        priority: str,
        first_alert_time: str,
        latest_alert_time: str,
    ) -> None:
        super(Investigation, self).__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.title = title
        self.status = status
        self.source = source
        self.assignee_email = assignee_email
        self.alert_types = alert_types
        self.created_time = created_time
        self.created_time_ms = convert_string_to_unix_time(self.created_time)
        self.rrn = rrn
        self.priority = priority
        self.first_alert_time = first_alert_time
        self.latest_alert_time = latest_alert_time
        self.alerts = []

    def to_table(self):
        return {
            "Title": self.title,
            "Status": self.status,
            "Source": self.source,
            "Assignee": self.assignee_email,
            "Alerts": DEFAULT_DELIMITER.join(self.alert_types),
            "Created Time": self.created_time,
        }

    def get_alert_info(
        self,
        alert_info: AlertInfo,
        environment_common: Union[
            EnvironmentHandleForFileSystem, EnvironmentHandleForDBSystem
        ],
        device_product_field: str,
    ) -> AlertInfo:
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.rrn
        alert_info.display_id = f"Rapid7InsightIDR_{self.rrn}"
        alert_info.name = self.title
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.flat_raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.source
        alert_info.source_grouping_identifier = self.title
        alert_info.start_time = convert_string_to_unix_time(self.first_alert_time)
        alert_info.end_time = convert_string_to_unix_time(self.latest_alert_time)
        alert_info.events = self.to_events()

        return alert_info

    def get_siemplify_severity(self) -> int:
        return SEVERITY_MAPPING.get(self.priority, -1)

    def to_events(self) -> List[dict]:
        event_data = copy.deepcopy(self.raw_data)
        event_data["data_type"] = "Investigation"
        events = [dict_to_flat(event_data)]
        for alert in self.alerts:
            alert["data_type"] = "Alert"
            events.append(dict_to_flat(alert))
        return events


class SavedQuery(BaseModel):
    def __init__(
        self, raw_data, id, name, statement, time_range, start_time, end_time, logs
    ):
        super(SavedQuery, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.statement = statement
        self.time_range = time_range
        self.start_time = start_time
        self.end_time = end_time
        self.logs = logs

    def to_table(self):
        return {
            "ID": self.id,
            "Name": self.name,
            "Statement": self.statement,
            "Time Range ": self.time_range,
            "Start Time": self.start_time,
            "End Time": self.end_time,
            "Logs": DEFAULT_DELIMITER.join(self.logs),
        }
