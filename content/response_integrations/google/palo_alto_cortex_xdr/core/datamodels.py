# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from abc import ABCMeta, abstractmethod
import base64
import dataclasses

from soar_sdk.SiemplifyUtils import add_prefix_to_dict, dict_to_flat

from TIPCommon.types import SingleJson

from ..core.constants import (
    API_AGENT_FQDN_KEY,
    API_ENDPOINT_DATA_KEY,
    API_ENDPOINT_KEY,
    API_ENDPOINT_NAME_KEY,
    API_HOST_NAME_KEY,
    EMPTY_RESULT,
    INTEGRATION_NAME,
)


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    api_key: str
    api_key_id: str
    verify_ssl: bool


class AbstractData(metaclass=ABCMeta):
    """
    Abstract Data Model for others Data Models
    """

    def to_csv(self):
        return dict_to_flat(self.to_json())

    @abstractmethod
    def to_json(self):
        pass

    def as_enrichment_data(self):
        return add_prefix_to_dict(self.to_csv(), INTEGRATION_NAME)


class Endpoint(AbstractData):
    def __init__(
        self,
        raw_data,
        endpoint_id=None,
        endpoint_name=None,
        endpoint_type=None,
        endpoint_status=None,
        os_type=None,
        ip=None,
        users=None,
        domain=None,
        first_seen=None,
        last_seen=None,
        endpoint_version=None,
        is_isolated=None,
        group_name=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.endpoint_id = endpoint_id
        self.endpoint_name = endpoint_name
        self.endpoint_type = endpoint_type
        self.endpoint_status = endpoint_status
        self.os_type = os_type
        self.ip = ip
        self.users = users
        self.domain = domain
        self.first_seen = first_seen
        self.last_seen = last_seen
        self.endpoint_version = endpoint_version
        self.is_isolated = is_isolated
        self.group_name = group_name

    def as_csv(self):
        return {
            "ID": self.endpoint_id,
            "Name": self.endpoint_name,
            "Type": self.endpoint_type,
            "Status": self.endpoint_status,
            "OS": self.os_type,
            "IP Address": self.ip,
            "Users": ", ".join(self.users),
            "Domain": self.domain,
            "First Seen": self.first_seen,
            "Last Seen": self.last_seen,
            "Endpoint Version": self.endpoint_version,
            "Is Isolated": self.is_isolated,
            "Group name": self.group_name,
        }

    def to_json(self):
        return self.raw_data

    def as_enrichment_data(self):
        return dict_to_flat(self.as_csv())


class DeviceViolation(AbstractData):
    def __init__(
        self,
        raw_data,
        violation_id=None,
        hostname=None,
        username=None,
        ip=None,
        timestamp=None,
        type=None,
        vendor=None,
        product=None,
        serial=None,
        endpoint_id=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.violation_id = violation_id
        self.hostname = hostname
        self.username = username
        self.ip = ip
        self.timestamp = timestamp
        self.type = type
        self.vendor = vendor
        self.product = product
        self.serial = serial
        self.endpoint_id = endpoint_id

    def to_csv(self):
        return {
            "ID": self.violation_id,
            "Hostname": self.hostname,
            "Username": self.username,
            "IP Address": self.ip,
            "Type": self.type,
            "Timestamp": self.timestamp,
            "Vendor": self.vendor,
            "Product": self.product,
            "Serial": self.serial,
            "Endpoint ID": self.endpoint_id,
        }

    def to_json(self):
        return self.raw_data

    def as_enrichment_data(self):
        return dict_to_flat(self.to_csv())


class AgentReport(AbstractData):
    def __init__(
        self,
        raw_data,
        TIMESTAMP=None,
        RECEIVEDTIME=None,
        ENDPOINTID=None,
        ENDPOINTNAME=None,
        DOMAIN=None,
        TRAPSVERSION=None,
        CATEGORY=None,
        TYPE=None,
        SUBTYPE=None,
        RESULT=None,
        REASON=None,
        DESCRIPTION=None,
        **kwargs,
    ):
        self.raw_data = raw_data
        self.timestamp = TIMESTAMP
        self.received_time = RECEIVEDTIME
        self.endpoint_id = ENDPOINTID
        self.endpoint_name = ENDPOINTNAME
        self.domain = DOMAIN
        self.traps_version = TRAPSVERSION
        self.category = CATEGORY
        self.type = TYPE
        self.sub_type = SUBTYPE
        self.result = RESULT
        self.reason = REASON
        self.description = DESCRIPTION

    def as_csv(self):
        return {
            "Timestamp": self.timestamp,
            "Received Time": self.received_time,
            "Endpoint ID": self.endpoint_id,
            "Endpoint Name": self.endpoint_name,
            "Domain": self.domain,
            "TRAPS Version": self.traps_version,
            "Category": self.category,
            "Type": self.type,
            "Subtype": self.sub_type,
            "Result": self.result,
            "Reason": self.reason,
            "Description": self.description,
        }

    def to_json(self):
        return self.raw_data

    def as_enrichment_data(self):
        return dict_to_flat(self.as_csv())


@dataclasses.dataclass(slots=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self):
        return self.raw_data


@dataclasses.dataclass(slots=True)
class IncidentInfo(BaseModel):
    raw_data: SingleJson
    incident_id: str
    description: str
    severity: str
    creation_time: int
    modification_time: int
    status: str
    starred: bool
    assigned_user_mail: str | None = None
    assigned_user_pretty_name: str | None = None
    aggregated_score: int | None = None

    @classmethod
    def from_json(cls, incident_data: SingleJson):
        return cls(
            raw_data=incident_data,
            incident_id=incident_data.get("incident_id"),
            description=incident_data.get("description"),
            severity=incident_data.get("severity"),
            creation_time=incident_data.get("creation_time"),
            modification_time=incident_data.get("modification_time"),
            status=incident_data.get("status"),
            starred=incident_data.get("starred"),
            assigned_user_mail=incident_data.get("assigned_user_mail"),
            assigned_user_pretty_name=incident_data.get("assigned_user_pretty_name"),
            aggregated_score=incident_data.get("aggregated_score"),
        )


@dataclasses.dataclass(slots=True)
class FileArtifact(BaseModel):
    raw_data: SingleJson
    file_hash: str
    file_name: str
    file_path: str
    file_wildcard_path: str

    @classmethod
    def from_json(cls, artifact_data: SingleJson):
        return cls(
            raw_data=artifact_data,
            file_hash=artifact_data.get("file_hash"),
            file_name=artifact_data.get("file_name"),
            file_path=artifact_data.get("file_path"),
            file_wildcard_path=artifact_data.get("file_wildcard_path"),
        )


@dataclasses.dataclass(slots=True)
class NetworkArtifact(BaseModel):
    raw_data: SingleJson
    network_remote_ip: str
    network_remote_port: int
    network_country: str
    network_domain: str

    @classmethod
    def from_json(cls, artifact_data: SingleJson):
        return cls(
            raw_data=artifact_data,
            network_remote_ip=artifact_data.get("network_remote_ip"),
            network_remote_port=artifact_data.get("network_remote_port"),
            network_country=artifact_data.get("network_country"),
            network_domain=artifact_data.get("network_domain"),
        )


@dataclasses.dataclass(slots=True)
class IncidentExtraData(BaseModel):
    raw_data: SingleJson
    incident: IncidentInfo
    alerts: list[Alert]
    file_artifacts: list[FileArtifact]
    network_artifacts: list[NetworkArtifact]

    @classmethod
    def from_json(cls, extra_data: SingleJson):
        return cls(
            raw_data=extra_data,
            incident=IncidentInfo.from_json(extra_data.get("incident", {})),
            alerts=[
                Alert.from_json(alert)
                for alert in extra_data.get("alerts", {}).get("data", [])
            ],
            file_artifacts=[
                FileArtifact.from_json(artifact)
                for artifact in extra_data.get("file_artifacts", {}).get("data", [])
            ],
            network_artifacts=[
                NetworkArtifact.from_json(artifact)
                for artifact in extra_data.get("network_artifacts", {}).get("data", [])
            ],
        )


@dataclasses.dataclass(slots=True)
class XQLSearch(BaseModel):
    raw_data: SingleJson
    query_id: str

    @classmethod
    def from_json(cls, raw_data: SingleJson):
        return cls(raw_data=raw_data, query_id=raw_data["reply"])


@dataclasses.dataclass(slots=True)
class XQLSearchEvent(BaseModel):
    raw_data: SingleJson
    event_id: str
    event_type: str
    event_sub_type: str
    insert_timestamp: int

    @classmethod
    def from_json(cls, raw_data: SingleJson):
        return cls(
            raw_data=raw_data,
            event_id=raw_data.get("event_id", ""),
            event_type=raw_data.get("event_type", ""),
            event_sub_type=raw_data.get("event_sub_type", ""),
            insert_timestamp=raw_data.get("insert_timestamp", EMPTY_RESULT),
        )


@dataclasses.dataclass(slots=True)
class XQLSearchResult(BaseModel):
    raw_data: SingleJson
    status: str
    events: list[XQLSearchEvent]
    number_of_results: int | None = None
    query_cost_charged: dict[str, float] | None = None
    remaining_quota: int | None = None

    @classmethod
    def from_json(cls, raw_data: SingleJson):
        return cls(
            raw_data=raw_data,
            status=raw_data["status"],
            events=[
                XQLSearchEvent.from_json(event)
                for event in raw_data.get("results", {}).get("data", [])
            ],
            number_of_results=raw_data.get("number_of_results", EMPTY_RESULT),
            query_cost_charged=raw_data.get("query_cost_charged"),
            remaining_quota=raw_data.get("remaining_quota"),
        )


@dataclasses.dataclass(slots=True)
class Incident(BaseModel):
    raw_data: SingleJson
    incident_id: str
    alerts: list[Alert]

    @classmethod
    def from_json(cls, incident_data: SingleJson):
        return cls(
            raw_data=incident_data,
            incident_id=incident_data["incident"]["incident_id"],
            alerts=[
                Alert.from_json(alert)
                for alert in incident_data.get("alerts", {}).get("data", [])
            ],
        )


@dataclasses.dataclass(slots=True)
class Alert(BaseModel):
    raw_data: SingleJson
    alert_id: str
    severity: str

    @classmethod
    def from_json(cls, alert_data: SingleJson):
        return cls(
            raw_data=alert_data,
            alert_id=alert_data["alert_id"],
            severity=alert_data["severity"],
        )

    def to_json(self) -> SingleJson:
        self.raw_data["fw_misc"] = convert_string_to_base64(
            self.raw_data.get("fw_misc", "")
        )
        self.raw_data["description"] = convert_string_to_base64(
            self.raw_data.get("description", "")
        )

        if not self.raw_data.get(API_HOST_NAME_KEY):
            endpoint_data = (
                self.raw_data.get(API_ENDPOINT_DATA_KEY)
                or self.raw_data.get(API_ENDPOINT_KEY)
            )
            if isinstance(endpoint_data, dict):
                host_name = endpoint_data.get(API_HOST_NAME_KEY) or endpoint_data.get(
                    API_ENDPOINT_NAME_KEY
                )
                if host_name:
                    self.raw_data[API_HOST_NAME_KEY] = host_name

            if not self.raw_data.get(API_HOST_NAME_KEY):
                host_name = self.raw_data.get(API_AGENT_FQDN_KEY)
                if host_name:
                    self.raw_data[API_HOST_NAME_KEY] = host_name

        return self.raw_data


def convert_string_to_base64(string="") -> str:
    if string is None:
        return ""

    return base64.b64encode(string.encode("utf-8")).decode("utf-8")
