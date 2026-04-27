from __future__ import annotations
import uuid
from typing import Optional, Union, List
from TIPCommon import flat_dict_to_csv, dict_to_flat
from copy import deepcopy
from .consts import (
    INCIDENT_RISK_LEVEL_MAPPING,
    DEFAULT_DEVICE_VENDOR,
    INCIDENT_SEARCH_TYPE,
    LOG_POINT_TO_SIEM_PRIORITIES,
)


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat())

    def is_empty(self):
        return not bool(self.raw_data)


class Repo:
    """
    LogPoint Repo
    """

    def __init__(self, raw_data, repo=None, address=None):
        """
        Repo Constructor
        """
        self.raw_data = raw_data
        self.repo = repo or ""
        self.address = address or ""

    def as_json(self):
        return {"repo": self.repo, "address": self.address}

    def as_csv(self):
        return {"Name": self.repo, "Address": self.address}


class QueryJob:
    def __init__(
        self,
        raw_data: dict,
        search_id: Optional[str] = None,
        client_type: Optional[str] = None,
        query_filter: Optional[str] = None,
        latest: Optional[bool] = None,
        lookup: Optional[bool] = None,
        query_type: Optional[str] = None,
        time_range: Union[List[int], str] = None,
        success: Optional[bool] = None,
    ):
        self.raw_data = raw_data
        self.search_id = search_id
        self.client_type = client_type
        self.query_filter = query_filter
        self.latest = latest
        self.lookup = lookup
        self.query_type = query_type
        self.time_range = time_range
        self.success = success


class QueryResults:
    class QueryRow:
        def __init__(self, raw_data):
            self.raw_data = raw_data

        def as_json(self):
            return self.raw_data

        def as_csv(self):
            return self.raw_data

    def __init__(
        self,
        raw_data,
        query_type: Optional[str] = None,
        query_rows: Optional[List[QueryRow]] = None,
        original_search_id: Optional[str] = None,
        final: Optional[bool] = None,
        success: Optional[str] = None,
    ):
        self.raw_data = raw_data
        self.query_type = query_type
        self.query_rows = query_rows
        self.original_search_id = original_search_id
        self.final = final
        self.success = success

    @property
    def finished(self):
        return bool(self.final)


class IncidentDetails(BaseModel):
    def __init__(self, raw_data, participating_events):
        super().__init__(raw_data)
        self.participating_events = participating_events


class IncidentEvent(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)


class Incident(BaseModel):
    def __init__(
        self,
        raw_data,
        id=None,
        detection_id=None,
        incident_id=None,
        alert_obj_id=None,
        type="",
        name=None,
        description=None,
        status=None,
        risk_level="",
        rows_count=None,
        detection_timestamp=None,
        time_range=None,
        query=None,
        user_id=None,
    ):
        super().__init__(raw_data)
        self.incident_id = incident_id
        self.id = id
        self.detection_id = detection_id
        self.alert_obj_id = alert_obj_id
        self.type = type
        self.name = name
        self.alert_name = name
        self.rule_name = name
        self.detection_timestamp = detection_timestamp
        self.timestamp = int(detection_timestamp * 1000)
        self.description = description
        self.status = status
        self.rows_count = rows_count
        self.risk_level = risk_level
        self.risk_level_value = INCIDENT_RISK_LEVEL_MAPPING.get(self.risk_level.lower())
        self.time_range = time_range
        self.query = query
        self.user_id = user_id

    def is_search_type(self):
        return self.type.lower() == INCIDENT_SEARCH_TYPE.lower()

    def get_alert_info(self, alert_info, environment_common, events):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.to_json())
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.alert_name
        alert_info.description = self.description
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = DEFAULT_DEVICE_VENDOR
        alert_info.priority = self.get_severity()
        alert_info.rule_generator = f"{self.type}: {self.name}"
        alert_info.end_time = alert_info.start_time = int(
            self.detection_timestamp * 1000
        )
        alert_info.events = self.create_events(events)
        alert_info.extensions = self.to_extensions()

        return alert_info

    def get_severity(self):
        return LOG_POINT_TO_SIEM_PRIORITIES.get(self.risk_level.lower(), -1)

    def create_events(self, events):
        if not events:
            return [self.to_flat()]

        merged_events = []
        for event in events:
            incident_data = deepcopy(self.to_flat())
            incident_data["event"] = event.to_json()
            merged_events.append(dict_to_flat(incident_data))

        return merged_events

    def to_extensions(self):
        return dict_to_flat(self.raw_data)


class User(BaseModel):
    def __init__(self, raw_data, user_id, username):
        super().__init__(raw_data)
        self.user_id = user_id
        self.username = username
