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
from .datamodels import *


class AttivoParser:
    def build_events_list(self, raw_data):
        return [self.build_event_object(item) for item in raw_data]

    def build_event_object(self, raw_data):
        return Event(
            raw_data=raw_data,
            id=raw_data.get("esID"),
            attack_name=raw_data.get("attackName"),
            attack_desc=raw_data.get("attackDesc"),
            severity=raw_data.get("details", {}).get("Severity"),
            timestamp=raw_data.get("timeStamp"),
        )

    def build_hostname_object(self, raw_data):
        raw_data = raw_data.get("result", {}).get("hits", {}).get("hits", [])
        item_data = raw_data[0].get("_source", {}) if raw_data else {}
        if item_data:
            return Hostname(
                raw_data=item_data,
                id=item_data.get("id"),
                hostname=item_data.get("hostName"),
                os=item_data.get("osName"),
                ip_addresses=", ".join(
                    [
                        interface.get("ipAddress")
                        for interface in item_data.get("interfaces", [])
                    ]
                ),
                mac_addresses=", ".join(
                    [
                        interface.get("macAddress")
                        for interface in item_data.get("interfaces", [])
                    ]
                ),
                usernames=", ".join(
                    [info.get("userName") for info in item_data.get("usersInfo", [])]
                ),
                os_type=item_data.get("osType"),
                system_type=item_data.get("systemtype"),
                uptime=item_data.get("uptime"),
            )

    def build_threatpaths_list(self, raw_data):
        return [
            self.build_threatpath_object(item) for item in raw_data.get("paths", [])
        ]

    def build_critical_threatpaths_list(self, raw_data):
        return [
            self.build_threatpath_object(item)
            for item in raw_data.get("criticalPaths", [])
        ]

    def build_threatpath_object(self, raw_data):
        return ThreatPath(
            raw_data=raw_data,
            dest_ip=raw_data.get("destIp"),
            src_ip=raw_data.get("srcIp"),
            src_hostname=raw_data.get("srcHostName"),
            dest_hostname=raw_data.get("destHostName"),
            cr_rulename=raw_data.get("crRuleName"),
            credential=raw_data.get("credential"),
            desc=raw_data.get("desc"),
            critical=raw_data.get("critical"),
            severity=raw_data.get("severity"),
            service=raw_data.get("service"),
            category=raw_data.get("category"),
            permission_name=raw_data.get("permissionName"),
        )

    def build_credentials_list(self, raw_data):
        return [
            self.build_credential_object(item)
            for item in raw_data.get("report", {})
            .get("endpoint_details", {})
            .get("d", {})
            .get("credentials", [])
        ]

    def build_credential_object(self, raw_data):
        return Credential(
            raw_data=raw_data,
            is_deceptive=raw_data.get("isDeceptive"),
            service=raw_data.get("service"),
            domain=raw_data.get("domain"),
            server_ip=raw_data.get("serverIp"),
            is_shortcut=raw_data.get("isShortcut"),
        )
