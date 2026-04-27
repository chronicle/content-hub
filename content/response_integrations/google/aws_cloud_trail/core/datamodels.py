from __future__ import annotations
import copy
import uuid

from TIPCommon import dict_to_flat

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from .consts import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    CLOUD_TRAIL_TO_SIEMPLIFY_PRIORITIES,
    TIME_FORMAT,
)


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def as_json(self):
        return self.raw_data


class InsightEvent(BaseModel):
    """
    Insight Event data model
    """

    def __init__(
        self,
        raw_data,
        event_id=None,
        event_name=None,
        event_time=None,
        event_source=None,
        username=None,
        cloud_trail_event=None,
    ):
        super(InsightEvent, self).__init__(raw_data)
        self.event_id = event_id
        self.event_name = event_name
        self.event_time = event_time
        self.event_time_str = self.event_time.strftime(TIME_FORMAT)
        self.event_source = event_source
        self.username = username
        self.cloud_trail_event = cloud_trail_event

        try:
            self.event_time_ms = convert_datetime_to_unix_time(self.event_time)
        except Exception:
            self.event_time_ms = 1

    def as_event(self):
        raw_data = copy.deepcopy(self.raw_data)
        raw_data["CloudTrailEvent"] = self.cloud_trail_event
        return dict_to_flat(raw_data)

    def get_alert_info(self, environment_common, alert_severity) -> AlertInfo:
        """
        Get alert info from an insight
        :param alert_severity: Alert's severity. Possible values can be: Informational, Low, Medium, High, Critical
        :param environment_common: {EnvironmentHandle} EnvironmentHandle instance
        :return: {AlertInfo} Alert Info data model
        """
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(self.as_event())
        alert_info.ticket_id = self.event_id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = f"Insight: {self.event_name}"
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = CLOUD_TRAIL_TO_SIEMPLIFY_PRIORITIES.get(
            alert_severity.lower(), -1
        )
        alert_info.rule_generator = self.event_name
        alert_info.end_time = alert_info.start_time = self.event_time_ms
        alert_info.events = [self.as_event()]

        return alert_info
