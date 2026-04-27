from __future__ import annotations
from .constants import (
    SUMMARY_TO_GET_THREAT_ID,
    TASK_COMPLETED,
    TASK_IN_PROGRESS,
    TASK_FAILED,
)


from TIPCommon import dict_to_flat, flat_dict_to_csv, add_prefix_to_dict
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from dateutil.parser import parse
import uuid

DEFAULT_DEVICE_VENDOR = "McAfee"
DEFAULT_DEVICE_PRODUCT = "Mvision EDR"


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Detection(BaseModel):
    def __init__(self, raw_data):
        super(Detection, self).__init__(raw_data)

    def to_event(self):
        return dict_to_flat(self.raw_data)


class Threat(BaseModel):
    def __init__(
        self,
        raw_data,
        threat_id,
        name,
        priority,
        threat_type,
        hashes,
        first_detected,
        last_detected,
        detections=[],
    ):
        super(Threat, self).__init__(raw_data)
        self.threat_id = threat_id
        self.uuid = str(uuid.uuid4())
        self.name = name
        self.priority = priority
        self.threat_type = threat_type
        self.hashes = hashes
        self.first_detected = convert_datetime_to_unix_time(parse(first_detected))
        self.last_detected = convert_datetime_to_unix_time(parse(last_detected))
        self.detections = detections
        self.timestamp = self.last_detected

    def get_alert_info(self, alert_info, environment_common):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.threat_id
        alert_info.display_id = self.uuid
        alert_info.name = self.name
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = DEFAULT_DEVICE_PRODUCT
        alert_info.priority = self.priority
        alert_info.rule_generator = self.threat_type
        alert_info.start_time = self.first_detected
        alert_info.end_time = self.last_detected
        alert_info.extensions = self.hashes
        alert_info.events = [detection.to_event() for detection in self.detections]

        return alert_info


class Host(BaseModel):
    def __init__(
        self,
        raw_data,
        ma_guid,
        hostname,
        desc,
        last_boot_time,
        certainty,
        net_interfaces,
    ):
        super(Host, self).__init__(raw_data)
        self.ma_guid = ma_guid
        self.hostname = hostname
        self.desc = desc
        self.last_boot_time = last_boot_time
        self.certainty = certainty
        self.net_interfaces = net_interfaces

    def get_from_raw_json(self, key, default_value=None):
        return self.raw_data.get(key, default_value)

    def to_csv(self):
        return flat_dict_to_csv(
            {
                "maGuid": self.ma_guid,
                "hostname": self.hostname,
                "OS": self.desc,
                "lastBootTime": self.last_boot_time,
                "certainty": self.certainty,
                "ips": f'{" ".join([item.ip for item in self.net_interfaces])}',
            }
        )

    def to_enrichment_data(self, prefix=None):
        new_dict = {
            "maGuid": self.ma_guid,
            "hostname": self.hostname,
            "OS": self.desc,
            "lastBootTime": self.last_boot_time,
            "certainty": self.certainty,
            "ips": f'{" ".join([item.ip for item in self.net_interfaces])}',
        }
        data = dict_to_flat(new_dict)
        return add_prefix_to_dict(data, prefix) if prefix else data


class NetInterface(BaseModel):
    def __init__(self, raw_data, ip):
        super(NetInterface, self).__init__(raw_data)
        self.ip = ip


class TaskResponseModel(BaseModel):
    def __init__(self, raw_data, status_id, status, location, descriptions):
        super(TaskResponseModel, self).__init__(raw_data)
        self.status_id = status_id
        self.status = status
        self.location = location
        self.descriptions = descriptions


class ErrorDescription(BaseModel):
    def __init__(self, raw_data, desc):
        super(ErrorDescription, self).__init__(raw_data)
        self.desc = desc


class Case(BaseModel):
    """
    McAfee Mvision EDR Case model
    """

    def __init__(
        self,
        raw_data,
        name=None,
        summary=None,
        created=None,
        owner=None,
        self_link=None,
        status_link=None,
        priority_link=None,
        source=None,
        is_automatic=None,
        last_modified=None,
        investigated=None,
    ):
        super(Case, self).__init__(raw_data)
        self.name = name
        self.summary = summary
        self.created = created
        self.owner = owner
        self.self_link = self_link
        self.status_link = status_link
        self.priority_link = priority_link
        self.source = source
        self.is_automatic = is_automatic
        self.last_modified = last_modified
        self.investigated = investigated

    @property
    def threat_id(self):
        return (
            self.summary.split(" ")[-1]
            if self.summary and self.summary.startswith(SUMMARY_TO_GET_THREAT_ID)
            else None
        )

    @property
    def id(self):
        return self.self_link.split("/")[-1] if self.self_link else None


class TaskBase(BaseModel):
    """
    McAfee Mvision EDR Task Base model for inheritance
    """

    def __init__(self, raw_data, id=None, status=None):
        super(TaskBase, self).__init__(raw_data)
        self.id = id
        self.status = status

    @property
    def is_in_progress(self):
        return self.status == TASK_IN_PROGRESS

    @property
    def is_completed(self):
        return self.status == TASK_COMPLETED

    @property
    def is_failed(self):
        return self.status == TASK_FAILED


class Task(TaskBase):
    """
    McAfee Mvision EDR Task model
    """

    def __init__(self, raw_data, id=None, status=None, location=None):
        super(Task, self).__init__(raw_data, id, status)
        self.location = location


class TaskStatus(TaskBase):
    """
    McAfee Mvision EDR Task Status model
    """

    def __init__(
        self,
        raw_data,
        id=None,
        status=None,
        success_host_responses=None,
        error_host_responses=None,
    ):
        super(TaskStatus, self).__init__(raw_data, id, status)
        self.success_host_responses = success_host_responses
        self.error_host_responses = error_host_responses
