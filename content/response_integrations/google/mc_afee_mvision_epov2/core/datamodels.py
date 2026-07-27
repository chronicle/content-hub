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
from TIPCommon import dict_to_flat, add_prefix_to_dict
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from .constants import DEFAULT_VENDOR, DEFAULT_PRODUCT


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class Tag(BaseModel):
    def __init__(
        self, raw_data, tag_id, name=None, created_by=None, family=None, notes=None
    ):
        super(Tag, self).__init__(raw_data)
        self.tag_id = tag_id
        self.name = name
        self.created_by = created_by
        self.family = family
        self.notes = notes

    def to_table_data(self):
        return {
            "ID": self.tag_id,
            "Name": self.name,
            "Created by": self.created_by,
            "Family": self.family,
            "Notes": self.notes,
        }


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        name,
        ip,
        hostname,
        device_id,
        agent_guid,
        last_update,
        managed_state,
        os_platform,
        os_type,
        os_version,
        domain_name,
        computer_name,
        agent_version,
        username,
        tags,
    ):
        super(Device, self).__init__(raw_data)
        self.name = name
        self.ip = ip
        self.device_id = device_id
        self.agent_guid = agent_guid
        self.last_update = last_update
        self.managed_state = managed_state
        self.os_platform = os_platform
        self.os_type = os_type
        self.os_version = os_version
        self.hostname = hostname
        self.domain_name = domain_name
        self.computer_name = computer_name
        self.agent_version = agent_version
        self.username = username
        self.tags = tags or []

    def to_enrichment_data(self, prefix):
        return add_prefix_to_dict(dict_to_flat(self.raw_data), prefix)

    def to_table_data(self):
        return {
            "ID": self.device_id,
            "Agent GUID": self.agent_guid,
            "Agent Version": self.agent_version,
            "Name": self.name,
            "Hostname": self.hostname,
            "Domain Name": self.domain_name,
            "Computer Name": self.computer_name,
            "IP Address": self.ip,
            "Last Update": self.last_update,
            "OS Platform": self.os_platform,
            "OS Type": self.os_type,
            "OS Version": self.os_version,
            "Username": self.username,
            "Tags": " ".join(self.tags) if self.tags else "",
        }

    def to_insight(self):
        return (f"Host: {self.name}\nOS: {self.os_type}\nIP Address: {self.ip}"
                f"\nDNS Name: {self.hostname}\n"
                f"Tags: {', '.join(self.tags) if self.tags else ''}\n"
                f"Username: {self.username}\nAgent Version: {self.agent_version}")


class Event(BaseModel):
    def __init__(
        self,
        raw_data,
        timestamp=None,
        event_id=None,
        auto_guid=None,
        detected_utc=None,
        received_utc=None,
        agent_guid=None,
        analyzer_name=None,
        analyzer_hostname=None,
        analyzer_ipv4=None,
        source_ipv4=None,
        source_username=None,
        target_ipv4=None,
        target_port=None,
        threat_name=None,
        threat_type=None,
        threat_category=None,
        threat_event_id=None,
        threat_severity=0,
    ):
        super(Event, self).__init__(raw_data)
        self.timestamp = timestamp
        self.event_id = event_id
        self.auto_guid = auto_guid
        self.agent_guid = agent_guid
        self.detected_utc = detected_utc
        self.received_utc = received_utc
        self.agent_guid = agent_guid
        self.analyzer_name = analyzer_name
        self.analyzer_hostname = analyzer_hostname
        self.analyzer_ipv4 = analyzer_ipv4
        self.source_ipv4 = source_ipv4
        self.source_username = source_username
        self.target_ipv4 = target_ipv4
        self.target_port = target_port
        self.threat_name = threat_name
        self.threat_type = threat_type
        self.threat_category = threat_category
        self.threat_event_id = threat_event_id

        try:
            self.threat_severity = int(threat_severity)
        except Exception:
            self.threat_severity = 0

        try:
            self.timestamp_ms = convert_string_to_unix_time(self.timestamp)
        except Exception:
            self.timestamp_ms = 1

    def as_event(self):
        return dict_to_flat(self.raw_data.get("attributes", {}))

    def as_alert_info(self, environment_common):
        """
        Create an AlertInfo out of the current finding
        :param environment_common: {EnvironmentHandle} The environment common object for
                                   fetching the environment
        :return: {AlertInfo} The created AlertInfo object
        """
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(self.as_event())
        alert_info.ticket_id = self.event_id
        alert_info.display_id = self.event_id
        alert_info.name = self.threat_category
        alert_info.description = self.threat_name
        alert_info.device_vendor = DEFAULT_VENDOR
        alert_info.device_product = DEFAULT_PRODUCT
        alert_info.priority = self.siemplify_severity
        alert_info.rule_generator = self.analyzer_name
        alert_info.start_time = self.timestamp_ms
        alert_info.end_time = self.timestamp_ms
        alert_info.events = [self.as_event()]
        alert_info.source_grouping_identifier = self.threat_event_id
        return alert_info

    @property
    def siemplify_severity(self):
        # if self.threat_severity <= 1:
        #     return -1  # Info
        # elif self.threat_severity == 2:
        #     return 40  # Low
        # elif self.threat_severity == 3:
        #     return 60  # Medium
        # elif 4 <= self.threat_severity < 6:
        #     return 80 # High
        # else:
        #     return 100 # Critical
        return 60
