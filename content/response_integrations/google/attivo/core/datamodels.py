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
import uuid
import copy
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAP
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from .UtilsManager import convert_seconds_to_days_hours_minutes


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
    def __init__(self, raw_data, id, attack_name, attack_desc, severity, timestamp):
        super(Event, self).__init__(raw_data)
        self.uuid = str(uuid.uuid4())
        self.id = id
        self.attack_name = attack_name
        self.attack_desc = attack_desc
        self.severity = severity
        self.timestamp = timestamp

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.to_json())
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = self.uuid
        alert_info.name = self.attack_name
        alert_info.description = self.attack_desc
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_severity()
        alert_info.rule_generator = self.attack_name
        alert_info.end_time = alert_info.start_time = convert_string_to_unix_time(
            self.timestamp
        )
        alert_info.events = [self.as_event()]

        return alert_info

    def get_severity(self):
        return SEVERITY_MAP.get(self.severity, -1)

    def as_event(self):
        event_data = copy.deepcopy(self.raw_data)
        return dict_to_flat(event_data)


class Hostname(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        hostname,
        os,
        ip_addresses,
        mac_addresses,
        usernames,
        os_type,
        system_type,
        uptime,
    ):
        super(Hostname, self).__init__(raw_data)
        self.id = id
        self.hostname = hostname
        self.os = os
        self.ip_addresses = ip_addresses
        self.mac_addresses = mac_addresses
        self.usernames = usernames
        self.os_type = os_type
        self.system_type = system_type
        self.uptime = uptime
        self.threatpaths = []
        self.vulnerabilities = []
        self.creds = []

    def as_json(
        self, include_threatpaths, include_vulnerabilities, include_credentials
    ):
        json_data = copy.deepcopy(self.raw_data)
        if include_threatpaths:
            json_data["threatPaths"] = [
                threatpath.to_json() for threatpath in self.threatpaths
            ]
        if include_vulnerabilities:
            json_data["vulnerabilities"] = self.vulnerabilities
        if include_credentials:
            json_data["credentials"] = [cred.to_json() for cred in self.creds]
        return json_data

    def to_table(
        self,
        include_threatpaths,
        include_vulnerabilities,
        include_credentials,
        prefix=None,
    ):
        data = dict_to_flat(
            {
                "os": self.os,
                "ip": self.ip_addresses,
                "mac": self.mac_addresses,
                "hostname": self.hostname,
                "users": self.usernames,
                "type": f"{self.os_type} {self.system_type}",
                "uptime": convert_seconds_to_days_hours_minutes(int(self.uptime)),
            }
        )

        if include_threatpaths:
            data["num_threatpaths"] = len(self.threatpaths)
        if include_vulnerabilities:
            data["num_vulnerabilities"] = len(self.vulnerabilities)
        if include_credentials:
            data["num_deceptive_creds"] = len(
                [cred for cred in self.creds if cred.is_deceptive]
            )
            data["num_real_creds"] = len(
                [cred for cred in self.creds if not cred.is_deceptive]
            )

        data = {key: value for key, value in data.items() if value is not None}
        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_insight(
        self, include_threatpaths, include_vulnerabilities, include_credentials
    ):
        return (
            f"<p><strong>Hostname: </strong>{self.hostname}<br /><strong>IP: </strong>{self.ip_addresses}"
            f'<strong><br />OS: </strong>{self.os or "N/A"}<br /><strong>Users: </strong>{self.usernames}<strong>'
            f"<br />Type:&nbsp;</strong>{self.os_type} {self.system_type}<br />"
            f"<strong>Number Of Deceptive Credentials:&nbsp;</strong>"
            f'{len([cred for cred in self.creds if cred.is_deceptive]) if include_credentials else "N/A"}'
            f"<br /><strong>Number Of Real Credentials:&nbsp;</strong>"
            f'{len([cred for cred in self.creds if not cred.is_deceptive]) if include_credentials else "N/A"}'
            f"</p><h3>Vulnerabilities</h3><p>"
            f'{"<br>".join(self.vulnerabilities) if include_vulnerabilities else "N/A"}'
            f"</p><h3>ThreatPaths</h3><p>"
            f'{"<br>".join([tp.permission_name for tp in self.threatpaths]) if include_threatpaths else "N/A"}</p>'
        )


class ThreatPath(BaseModel):
    def __init__(
        self,
        raw_data,
        dest_ip,
        src_ip,
        src_hostname,
        dest_hostname,
        cr_rulename,
        credential,
        desc,
        critical,
        severity,
        service,
        category,
        permission_name,
    ):
        super(ThreatPath, self).__init__(raw_data)
        self.dest_ip = dest_ip
        self.src_ip = src_ip
        self.src_hostname = src_hostname
        self.dest_hostname = dest_hostname
        self.cr_rulename = cr_rulename
        self.credential = credential
        self.desc = desc
        self.critical = critical
        self.severity = severity
        self.service = service
        self.category = category
        self.permission_name = permission_name

    def to_csv(self):
        return dict_to_flat(
            {
                "Dest IP": self.dest_ip,
                "Src IP": self.src_ip,
                "Src Host": self.src_hostname,
                "Dest Host": self.dest_hostname,
                "Name": self.cr_rulename,
                "Credential": self.credential,
                "Description": self.desc,
                "Critical": self.critical,
                "Severity": self.severity,
                "Service": self.service,
                "Category": self.category,
            }
        )


class Credential(BaseModel):
    def __init__(self, raw_data, is_deceptive, service, domain, server_ip, is_shortcut):
        super(Credential, self).__init__(raw_data)
        self.is_deceptive = is_deceptive
        self.service = service
        self.domain = domain
        self.server_ip = server_ip
        self.is_shortcut = is_shortcut

    def to_csv(self):
        return dict_to_flat(
            {
                "Deceptive": self.is_deceptive,
                "Service": self.service,
                "Domain": self.domain,
                "Server IP": self.server_ip,
                "Shortcut": self.is_shortcut,
            }
        )
