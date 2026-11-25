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
from .UtilsManager import convert_list_to_comma_string, convert_list_to_semicolon_string
from .constants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    SEVERITY_MAP,
    HOST_GROUPING,
    VULNERABILITY_GROUPING,
    DEFAULT_RULE_GEN,
    SEVERITY_REVERSE_MAP,
    SEVERITY_COLORS,
    BLACK_COLOR,
)
import uuid
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time


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


class Asset(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        ipv4,
        ipv6,
        netbios_name,
        has_agent,
        last_seen,
        tags,
        hostname,
        operating_system,
        mac_address,
        system_type,
        fqdn,
        agent_names,
    ):
        super(Asset, self).__init__(raw_data)
        self.id = id
        self.ipv4 = ipv4
        self.ipv6 = ipv6
        self.netbios_name = netbios_name
        self.has_agent = has_agent
        self.last_seen = last_seen
        self.tags = tags
        self.hostname = hostname
        self.operating_system = operating_system
        self.mac_address = mac_address
        self.system_type = system_type
        self.fqdn = fqdn
        self.agent_names = agent_names

    def _build_data_dict(self, delimiter_func):
        return {
            "has_agent": self.has_agent,
            "last_seen": self.last_seen,
            "tags": delimiter_func(self.tags),
            "ipv4": delimiter_func(self.ipv4),
            "ipv6": delimiter_func(self.ipv6),
            "netbios_name": delimiter_func(self.netbios_name),
            "hostname": delimiter_func(self.hostname),
            "OS": delimiter_func(self.operating_system),
            "mac_address": delimiter_func(self.mac_address),
            "system_type": delimiter_func(self.system_type),
            "fqdn": delimiter_func(self.fqdn),
            "agent_names": delimiter_func(self.agent_names),
        }

    def to_enrichment_data(self, prefix=None):
        data = self._build_data_dict(convert_list_to_comma_string)
        flat_data = dict_to_flat(data)

        filtered_data = {
            key: value for key, value in flat_data.items() if value is not None
        }
        return add_prefix_to_dict(filtered_data, prefix) if prefix else filtered_data

    def to_table(self):
        data = self._build_data_dict(convert_list_to_semicolon_string)
        flat_data = dict_to_flat(data)

        return {key: value for key, value in flat_data.items() if value is not None}

    def as_insight(self):
        return (
            "<p>"
            f"<strong>IP: </strong>{convert_list_to_comma_string(self.ipv4) or 'N/A'}"
            "<strong><br />Mac Address: </strong>"
            f"{convert_list_to_comma_string(self.mac_address) or 'N/A'}"
            "<strong><br />NetBIOS: </strong>"
            f"{convert_list_to_comma_string(self.netbios_name) or 'N/A'}<br />"
            "<strong>Hostname: </strong>"
            f"{convert_list_to_comma_string(self.hostname) or 'N/A'}<br />"
            "<strong>Agent Names: </strong>"
            f"{convert_list_to_comma_string(self.agent_names) or 'N/A'}<br />"
            "<strong>OS: </strong>"
            f"{convert_list_to_comma_string(self.operating_system) or 'N/A'}<br />"
            "<strong>System Type: </strong>"
            f"{convert_list_to_comma_string(self.system_type) or 'N/A'}"
            "</p>"
        )


class Vulnerability(BaseModel):
    def __init__(self, raw_data, id, asset_id, ipv4, description, severity, last_found):
        super(Vulnerability, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = id
        self.asset_id = asset_id
        self.ipv4 = ipv4
        self.description = description
        self.severity = severity
        self.last_found = last_found

    def get_alert_info(
        self,
        alert_info,
        environment_common,
        device_product_field,
        grouping_mechanism,
        vulnerabilities_group,
    ):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = (
            self.id if grouping_mechanism == VULNERABILITY_GROUPING else str(self.uuid)
        )
        alert_info.display_id = str(self.uuid)
        alert_info.name = (
            f"{self.ipv4}: New Vulnerabilities Found"
            if grouping_mechanism == HOST_GROUPING
            else (
                "New Vulnerability Found"
                if grouping_mechanism == VULNERABILITY_GROUPING
                else f"{self.ipv4}: New Vulnerability {self.id}"
            )
        )
        if grouping_mechanism != HOST_GROUPING:
            alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity(vulnerabilities_group)
        alert_info.rule_generator = DEFAULT_RULE_GEN
        alert_info.start_time = alert_info.end_time = convert_string_to_unix_time(
            self.last_found
        )
        alert_info.events = self.create_events(vulnerabilities_group)

        return alert_info

    def to_json(self):
        self.raw_data["event_type"] = "Vulnerability"
        return self.raw_data

    def get_siemplify_severity(self, vulnerabilities_group):
        return SEVERITY_MAP.get(
            max([vulnerability.severity for vulnerability in vulnerabilities_group]), -1
        )

    def create_events(self, vulnerabilities_group):
        return [
            dict_to_flat(vulnerability.to_json())
            for vulnerability in vulnerabilities_group
        ]


class PluginFamily(BaseModel):
    def __init__(self, raw_data, id, name, count):
        super(PluginFamily, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.count = count

    def to_csv(self):
        return dict_to_flat({"Name": self.name, "Count": self.count})


class VulnerabilityDetails(BaseModel):
    def __init__(self, raw_data, synopsis, solution, severity, family, plugin_id):
        super(VulnerabilityDetails, self).__init__(raw_data)
        self.synopsis = synopsis
        self.solution = solution
        self.severity = severity
        self.family = family
        self.plugin_id = plugin_id

    def to_json(self):
        self.raw_data["plugin_id"] = self.plugin_id
        self.raw_data["info"]["severity"] = self.get_mapped_severity()
        self.raw_data["info"]["plugin_details"]["severity"] = self.get_mapped_severity()
        return self.raw_data

    def get_mapped_severity(self):
        return SEVERITY_REVERSE_MAP.get(self.severity, "Info")

    def to_table(self):
        return dict_to_flat(
            {
                "ID": self.plugin_id,
                "Severity": self.get_mapped_severity(),
                "Synopsis": self.synopsis,
                "Solution": self.solution,
                "Family": self.family,
            }
        )

    def as_insight(self):
        content = (
            f'<br><strong>Vulnerability: {self.plugin_id}. Severity: <span style="color: '
            f'{SEVERITY_COLORS.get(self.severity, BLACK_COLOR)};"> {self.get_mapped_severity()}</strong><br>'
        )
        content += "<p>"
        content += f"<br><strong>Synopsis</strong>"
        content += f"<br>{self.synopsis}"
        content += f"<br><strong>Solution</strong>"
        content += f"<br>{self.solution}"
        content += "</p>"

        return content


class EndpointVulnerability(BaseModel):
    def __init__(self, raw_data, id, name, severity, family, count=None):
        super(EndpointVulnerability, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.severity = severity
        self.family = family
        self.count = count

    def get_mapped_severity(self):
        return SEVERITY_REVERSE_MAP.get(self.severity, "Info")

    def to_json(self):
        self.raw_data["severity"] = self.get_mapped_severity()
        return self.raw_data

    def to_table(self):
        return dict_to_flat(
            {
                "ID": self.id,
                "Name": self.name,
                "Severity": self.get_mapped_severity(),
                "Family": self.family,
            }
        )

    def to_scan_table(self):
        return dict_to_flat(
            {
                "ID": self.id,
                "Name": self.name,
                "Severity": self.get_mapped_severity(),
                "Family": self.family,
                "Count": self.count,
            }
        )


class Policy(BaseModel):
    def __init__(self, raw_data, id, name, description, visibility, uuid):
        super(Policy, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.description = description
        self.visibility = visibility
        self.uuid = uuid

    def to_csv(self):
        return dict_to_flat(
            {
                "Name": self.name,
                "Visibility": self.visibility,
                "Description": self.description,
            }
        )


class Scanner(BaseModel):
    def __init__(self, raw_data, id, name, uuid, type, status):
        super(Scanner, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.uuid = uuid
        self.type = type
        self.status = status

    def to_csv(self):
        return dict_to_flat(
            {"Name": self.name, "Type": self.type, "Status": self.status}
        )


class Scan(BaseModel):
    def __init__(self, raw_data, vulnerabilities):
        super(Scan, self).__init__(raw_data)
        self.vulnerabilities = vulnerabilities

    def to_json(self):
        self.raw_data.pop("filters", None)
        for item in self.raw_data.get("vulnerabilities", []):
            item["severity"] = SEVERITY_REVERSE_MAP.get(item.get("severity", 0), "Info")
        return self.raw_data

    def to_csv(self):
        csv_data = []
        for item in self.vulnerabilities:
            csv_data.append(item.to_scan_table())
        return csv_data
