from __future__ import annotations
import copy
import json

from typing import Optional, List
from TIPCommon import dict_to_flat
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from .consts import (
    DEVO_ALERT_PREFIX,
    DEVO_ALERT_DESCRIPTION,
    INTEGRATION_IDENTIFIER,
    ALERT_PRIORITY_TO_SIEM_SEVERITY,
    MAPPED_ALERT_STATUSES,
)
from urllib.parse import unquote_plus


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def is_empty(self):
        return not bool(self.raw_data)


class QueryResult(BaseModel):
    """
    Devo Security Auth API User
    """

    def __init__(
        self,
        raw_data: Optional[dict],
        msg: Optional[str] = None,
        error: Optional[str] = None,
        timestamp: Optional[int] = None,
        cid: Optional[str] = None,
        status: Optional[str] = None,
        objects: Optional[List] = None,
    ):
        super(QueryResult, self).__init__(raw_data)
        self.raw_data = raw_data
        self.msg = msg
        self.error = error
        self.timestamp = timestamp
        self.cid = cid
        self.status = status
        self.objects = objects

    def to_json(self):
        copy_object_raw_data = copy.deepcopy(self.raw_data)
        if self.objects:
            copy_object_raw_data["object"] = [
                query_object.to_flat() for query_object in self.objects
            ]
        return copy_object_raw_data


class QueryObject(BaseModel):
    """
    Devo Query's objects
    """

    def __init__(
        self,
        raw_data: Optional[dict],
        eventdate: Optional[int] = None,
        alert_host: Optional[str] = None,
        domain: Optional[str] = None,
        priority: Optional[float] = None,
        context: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[int] = None,
        alert_id: Optional[str] = None,
        src_ip: Optional[str] = None,
        src_port: Optional[str] = None,
        src_host: Optional[str] = None,
        dst_ip: Optional[str] = None,
        dst_port: Optional[str] = None,
        dst_host: Optional[str] = None,
        protocol: Optional[str] = None,
        username: Optional[str] = None,
        application: Optional[str] = None,
        engine: Optional[str] = None,
        extra_data: Optional[str] = None,
    ):
        super(QueryObject, self).__init__(raw_data)
        self.raw_data = raw_data
        self.eventdate = eventdate
        self.alert_host = alert_host
        self.domain = domain
        self.priority = priority
        self.context = context
        self.category = category
        self.status = status
        self.alert_id = alert_id
        self.src_ip = src_ip
        self.src_port = src_port
        self.src_host = src_host
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.dst_host = dst_host
        self.protocol = protocol
        self.username = username
        self.application = application
        self.engine = engine
        self.extra_data = extra_data

    def to_alert_info(self, environment_common):
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(self.to_flat())
        alert_info.ticket_id = self.alert_id
        alert_info.display_id = self.alert_id
        alert_info.name = f"{DEVO_ALERT_PREFIX}: {self.context.split('.')[-1] or ''}"
        alert_info.reason = None
        alert_info.description = DEVO_ALERT_DESCRIPTION
        alert_info.device_vendor = INTEGRATION_IDENTIFIER
        alert_info.device_product = INTEGRATION_IDENTIFIER
        alert_info.priority = ALERT_PRIORITY_TO_SIEM_SEVERITY.get(self.priority, -1)
        alert_info.rule_generator = self.context
        alert_info.start_time = self.eventdate
        alert_info.end_time = self.eventdate
        alert_info.events = [self.to_flat()]
        return alert_info

    def to_json(self):
        copy_object_raw_data = copy.deepcopy(self.raw_data)
        if copy_object_raw_data.get("extraData", ""):
            try:
                _extra_data = {
                    key: unquote_plus(value)
                    for key, value in json.loads(
                        copy_object_raw_data.get("extraData", "")
                    ).items()
                }
                copy_object_raw_data["extraData"] = _extra_data
            except Exception:
                pass
        if copy_object_raw_data.get("status", "") is not None:
            copy_object_raw_data["status_text"] = MAPPED_ALERT_STATUSES.get(
                copy_object_raw_data.get("status", ""), ""
            )
        return copy_object_raw_data
