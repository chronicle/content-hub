from __future__ import annotations
import datetime

from copy import deepcopy
from typing import Dict
from TIPCommon import dict_to_flat, convert_datetime_to_unix_time
from .VaronisDataSecurityPlatformConstants import (
    ALERT_DATETIME_FORMAT,
    PRODUCT_NAME,
    SEVERITY_MAPIING,
)


class Base:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def as_json(self):
        return deepcopy(self.raw_data)

    def flat_data(self, additional_data: Dict = None):
        _data = self.as_json()
        _data.update({"device_product": PRODUCT_NAME})
        if additional_data is not None:
            _data.update(additional_data)
        return dict_to_flat(_data)


class Alert(Base):
    def __init__(self, alert_data):
        super().__init__(alert_data)
        self.abnormal_location = alert_data.get("AbnormalLocation")
        self.blacklist_location = alert_data.get("BlacklistLocation")
        self.category = alert_data.get("Category")
        self.close_reason = alert_data.get("CloseReason")
        self.id = alert_data.get("ID")
        self.severity = alert_data.get("Severity")
        self.status = alert_data.get("Status")
        self.time = alert_data.get("Time")
        self.name = alert_data.get("Name")
        self.alertseqid = alert_data.get("AlertSeqId")

        self.timestamp = convert_datetime_to_unix_time(
            datetime.datetime.strptime(self.time, ALERT_DATETIME_FORMAT)
        )

    def get_severity(self):
        return SEVERITY_MAPIING.get(self.severity, -1)


class Event(Base):
    pass
