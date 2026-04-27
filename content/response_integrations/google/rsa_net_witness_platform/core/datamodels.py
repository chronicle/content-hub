from __future__ import annotations
import copy
import uuid

from TIPCommon import dict_to_flat, add_prefix_to_dict

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from .UtilsManager import convert_string_to_unix_time
from .constants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    DEFAULT_RULE_GENERATOR,
    SEVERITY_MAP,
)


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Event(BaseModel):

    def __init__(self, raw_data):
        super(Event, self).__init__(raw_data)

    def to_csv(self):
        formatted_csv = {}
        flat_raw_data = dict_to_flat(self.to_json())
        for key, value in flat_raw_data.items():
            formatted_csv[key.replace(".", " ")] = value

        return formatted_csv


class Service(BaseModel):

    def __init__(self, raw_data, id):
        super(Service, self).__init__(raw_data)
        self.id = id


class HostEntity(BaseModel):

    def __init__(
        self,
        raw_data,
        agent_id,
        hostname,
        risk_score,
        network_interfaces,
        last_seen_time,
    ):
        super(HostEntity, self).__init__(raw_data)
        self.agent_id = agent_id
        self.hostname = hostname
        self.risk_score = risk_score
        self.network_interfaces = network_interfaces
        self.last_seen_time = last_seen_time

    def to_enrichment_data(self, prefix=None):
        new_dict = self.to_json()
        for i, item in enumerate(self.network_interfaces):
            new_dict.update(
                {
                    f'{"networkInterfaces"}_{i}_{str(key)}': value
                    for key, value in item.to_json().items()
                }
            )
        del new_dict["networkInterfaces"]
        data = dict_to_flat(new_dict)
        return add_prefix_to_dict(data, prefix) if prefix else data


class NetworkInterface(BaseModel):

    def __init__(
        self,
        raw_data,
        name,
        mac_address,
        ipv4,
        ipv6,
        network_idv6,
        gateway,
        dns,
        promiscuous,
    ):
        super(NetworkInterface, self).__init__(raw_data)
        self.name = name
        self.mac_address = mac_address
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.network_idv6 = network_idv6
        self.gateway = gateway
        self.dns = dns
        self.promiscuous = promiscuous


class FileObject(BaseModel):

    def __init__(
        self,
        raw_data,
        filename,
        reputation_status,
        global_risk_score,
        machine_os_type,
        size,
        checksum_md5,
        checksum_sha1,
        checksum_sha256,
        entropy,
        format,
        file_status,
        remediation_action,
    ):
        super(FileObject, self).__init__(raw_data)
        self.filename = filename
        self.reputation_status = reputation_status
        self.global_risk_score = global_risk_score
        self.machine_os_type = machine_os_type
        self.size = size
        self.checksum_md5 = checksum_md5
        self.checksum_sha1 = checksum_sha1
        self.checksum_sha256 = checksum_sha256
        self.entropy = entropy
        self.format = format
        self.file_status = file_status
        self.remediation_action = remediation_action

    def to_enrichment_data(self, prefix=None):
        new_dict = {
            "filename": self.filename,
            "reputationStatus": self.reputation_status,
            "globalRiskScore": self.global_risk_score,
            "machineOsType": self.machine_os_type,
            "size": self.size,
            "checksumMd5": self.checksum_md5,
            "checksumSha1": self.checksum_sha1,
            "checksumSha256": self.checksum_sha256,
            "entropy": self.entropy,
            "format": self.format,
            "fileStatus": self.file_status,
            "remediationAction": self.remediation_action,
        }
        data = dict_to_flat(new_dict)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Incident(BaseModel):

    def __init__(
        self,
        raw_data,
        id=None,
        title=None,
        summary=None,
        priority=None,
        risk_score=None,
        status=None,
        alert_count=None,
        average_alert_risk_score=None,
        created=None,
        last_updated=None,
        rule_id=None,
        first_alert_time=None,
        created_by=None,
        event_count=None,
    ):
        super(Incident, self).__init__(raw_data)
        self.id = id
        self.title = title
        self.summary = summary
        self.priority = priority
        self.risk_score = risk_score
        self.status = status
        self.alert_count = alert_count
        self.average_alert_risk_score = average_alert_risk_score
        self.created = created
        self.last_updated = last_updated
        self.rule_id = rule_id
        self.first_alert_time = first_alert_time
        self.created_by = created_by
        self.event_count = event_count

        try:
            self.created_ms = convert_string_to_unix_time(self.created)
        except Exception:
            self.created_ms = 1

    def get_siemplify_severity(self):
        if 0 <= self.risk_score <= 40:
            return SEVERITY_MAP["Low"]
        elif 40 < self.risk_score <= 60:
            return SEVERITY_MAP["Medium"]
        elif 60 < self.risk_score <= 80:
            return SEVERITY_MAP["High"]
        elif 80 < self.risk_score <= 100:
            return SEVERITY_MAP["Critical"]

        return SEVERITY_MAP["Informational"]

    def as_alert_info(self, events, environment_common) -> AlertInfo:
        """
        Create an AlertInfo out of the current Incident alert.
        :param environment_common: {EnvironmentHandle} The environment common object for fetching the environment
        :param events: {list} List of the events of the alert info
        :return: {AlertInfo} An AlertInfo object
        """
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.title
        alert_info.description = self.summary
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.created_by or DEFAULT_RULE_GENERATOR
        alert_info.start_time = self.created_ms
        alert_info.end_time = self.created_ms
        alert_info.events = [self.as_event()] + events

        return alert_info

    def as_event(self):
        raw_event = copy.deepcopy(self.raw_data)
        raw_event["event_type"] = "Incident"
        return dict_to_flat(raw_event)


class ErrorObject(BaseModel):

    def __init__(self, raw_data, message):
        super(ErrorObject, self).__init__(raw_data)
        self.message = message


class IncidentAlert(BaseModel):
    class Event(BaseModel):
        def __init__(
            self, raw_data, domain=None, event_source=None, event_source_id=None
        ):
            super(IncidentAlert.Event, self).__init__(raw_data)
            self.domain = domain
            self.event_source = event_source
            self.event_source_id = event_source_id
            self.additional_data = None

        def as_event(self):
            raw_event = copy.deepcopy(self.raw_data)
            if self.additional_data:
                raw_event["additional_fields"] = {
                    data.type: data.value for data in self.additional_data
                }
            return dict_to_flat(raw_event)

    def __init__(
        self,
        raw_data,
        id=None,
        title=None,
        detail=None,
        created=None,
        source=None,
        risk_score=None,
        type=None,
        events=None,
    ):
        super(IncidentAlert, self).__init__(raw_data)
        self.id = id
        self.title = title
        self.detail = detail
        self.created = created
        self.source = source
        self.risk_score = risk_score
        self.type = type
        self.events = events

    def as_event(self, event: Event):
        raw_event = copy.deepcopy(self.raw_data)
        raw_event["event_type"] = "Alert"
        raw_event["events"] = [event.as_event()]
        return dict_to_flat(raw_event)


class EventMetadata(BaseModel):
    def __init__(self, raw_data, field_1=None, field_2=None):
        super(EventMetadata, self).__init__(raw_data)
        self.field_1 = field_1
        self.field_2 = field_2


class EventAdditionalData(BaseModel):
    def __init__(self, raw_data, type=None, value=None):
        super(EventAdditionalData, self).__init__(raw_data)
        self.type = type
        self.value = value
