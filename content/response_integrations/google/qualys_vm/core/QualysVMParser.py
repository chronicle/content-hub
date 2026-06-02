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
from .UtilsManager import read_csv


class QualysVMParser:

    def build_detections_list(self, raw_data: str) -> list[Detection]:
        raw_list = read_csv(raw_data.splitlines())
        headers = [key.replace(" ", "_") for key in raw_list[0]]
        list_of_dicts = [dict(zip(headers, row)) for row in raw_list[1:]]
        return [self.build_detection_object(item) for item in list_of_dicts]

    def build_detection_object(self, raw_data: dict) -> Detection:
        return Detection(
            raw_data=raw_data,
            id=raw_data.get("QID"),
            dns_name=raw_data.get("DNS_Name"),
            ip_address=raw_data.get("IP_Address"),
            result=raw_data.get("Results"),
            severity=raw_data.get("Severity"),
            first_found_datetime=raw_data.get("First_Found_Datetime"),
            status=raw_data.get("Status"),
            port=raw_data.get("Port"),
            detection_type=raw_data.get("Type"),
            host_id=raw_data.get("Host_ID"),
        )

    def _extract_os_and_primary_host(
        self, raw_data: dict | list[dict]
    ) -> tuple[str | None, dict | None]:
        """Extracts the operating system and primary host dictionary from raw data."""
        if isinstance(raw_data, list):
            os = None
            for host in raw_data:
                if isinstance(host, dict) and host.get("OS") is not None:
                    os = host.get("OS")
            host_dict = raw_data[0] if raw_data and isinstance(raw_data[0], dict) else None
            return os, host_dict

        if isinstance(raw_data, dict):
            return raw_data.get("OS"), raw_data

        return None, None

    def _extract_tags(self, tags_data: dict | None) -> str | None:
        """Extracts comma-separated tags from tags data structure."""
        if not isinstance(tags_data, dict):
            return None

        all_tags = tags_data.get("TAG")
        if isinstance(all_tags, list):
            tags_list = [
                tag.get("NAME")
                for tag in all_tags
                if isinstance(tag, dict) and tag.get("NAME")
            ]
            return ",".join(tags_list) if tags_list else None

        if isinstance(all_tags, dict):
            return all_tags.get("NAME")

        return None

    def build_host_object(self, raw_data: dict | list[dict]) -> Host:
        os_value, host_dict = self._extract_os_and_primary_host(raw_data)

        if not host_dict:
            return Host(raw_data=raw_data, os=os_value)

        dns_domain = None
        dns_fqdn = None
        dns_data = host_dict.get("DNS_DATA")
        if isinstance(dns_data, dict):
            dns_domain = dns_data.get("DOMAIN")
            dns_fqdn = dns_data.get("FQDN")

        return Host(
            raw_data=raw_data,
            ip_address=host_dict.get("IP"),
            netbios_name=host_dict.get("NETBIOS"),
            dns_domain=dns_domain,
            dns_fqdn=dns_fqdn,
            os=os_value,
            tags=self._extract_tags(host_dict.get("TAGS")),
            comment=host_dict.get("COMMENTS"),
        )

    def _parse_host_from_dict(self, raw_dict: dict) -> list[dict]:
        """Parses host dictionaries from a root dictionary structure."""
        host_data = raw_dict.get("HOST")
        if isinstance(host_data, list):
            return [h for h in host_data if isinstance(h, dict)]
        if isinstance(host_data, dict):
            return [host_data]
        return []

    def _parse_hosts_from_list(self, raw_list: list) -> list[dict]:
        """Parses host dictionaries from a list structure."""
        hosts_list = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue

            if "HOST" in item:
                hosts_list.extend(self._parse_host_from_dict(item))
            else:
                hosts_list.append(item)

        return hosts_list

    def _get_hosts_list(self, raw_data: dict | list[dict] | None) -> list[dict]:
        if not raw_data:
            return []

        if isinstance(raw_data, dict):
            return self._parse_host_from_dict(raw_data)

        if isinstance(raw_data, list):
            return self._parse_hosts_from_list(raw_data)

        return []

    def filter_hostname(
        self, raw_data: dict | list[dict] | None, hostname: str
    ) -> dict | list[dict]:
        hosts_list = self._get_hosts_list(raw_data)
        hostname_data = []
        for host_data in hosts_list:
            netbios = host_data.get("NETBIOS")
            dns_data = host_data.get("DNS_DATA")
            dns_hostname = (
                dns_data.get("HOSTNAME") if isinstance(dns_data, dict) else None
            )
            if netbios == hostname or dns_hostname == hostname:
                hostname_data.append(host_data)

        if len(hostname_data) == 1:
            return hostname_data[0]
        return hostname_data

    def get_ip_for_hostname(
        self, raw_data: dict | list[dict] | None, hostname: str
    ) -> str | None:
        hosts_list = self._get_hosts_list(raw_data)
        for host_data in hosts_list:
            netbios = host_data.get("NETBIOS")
            dns_data = host_data.get("DNS_DATA")
            dns_hostname = (
                dns_data.get("HOSTNAME") if isinstance(dns_data, dict) else None
            )
            if netbios == hostname or dns_hostname == hostname:
                return host_data.get("IP")

        return None

    def build_endpointdetection_object(
        self, raw_data: dict | None
    ) -> list[EndpointDetection]:
        if not isinstance(raw_data, dict):
            return []
        vuln_list_data = raw_data.get("VULN_LIST")
        vulnerabilities = (
            vuln_list_data.get("VULN") if isinstance(vuln_list_data, dict) else None
        )
        if not vulnerabilities:
            return []

        if isinstance(vulnerabilities, dict):
            return [
                EndpointDetection(
                    raw_data=vulnerabilities,
                    qid=vulnerabilities.get("QID"),
                    title=vulnerabilities.get("TITLE") or {},
                    diagnosis=vulnerabilities.get("DIAGNOSIS") or {},
                    consequence=vulnerabilities.get("CONSEQUENCE") or {},
                    solution=vulnerabilities.get("SOLUTION") or {},
                    patchable=vulnerabilities.get("PATCHABLE") or {},
                    category=vulnerabilities.get("CATEGORY") or {},
                    criticality_level=vulnerabilities.get("SEVERITY_LEVEL"),
                )
            ]

        elif isinstance(vulnerabilities, list):
            return [
                EndpointDetection(
                    raw_data=vulnerability,
                    qid=vulnerability.get("QID"),
                    title=vulnerability.get("TITLE") or {},
                    diagnosis=vulnerability.get("DIAGNOSIS") or {},
                    consequence=vulnerability.get("CONSEQUENCE") or {},
                    solution=vulnerability.get("SOLUTION") or {},
                    patchable=vulnerability.get("PATCHABLE") or {},
                    category=vulnerability.get("CATEGORY") or {},
                    criticality_level=vulnerability.get("SEVERITY_LEVEL"),
                )
                for vulnerability in vulnerabilities
                if isinstance(vulnerability, dict)
            ]

        return []

    def get_detection_quids(self, raw_data: dict | list[dict] | None) -> list[str]:
        quids = []
        hosts_list = self._get_hosts_list(raw_data)
        for host_data in hosts_list:
            detection_list_data = host_data.get("DETECTION_LIST")
            detection_list = (
                detection_list_data.get("DETECTION")
                if isinstance(detection_list_data, dict)
                else None
            )
            if not detection_list:
                continue
            if isinstance(detection_list, list):
                for detection in detection_list:
                    if isinstance(detection, dict) and detection.get("QID"):
                        quids.append(str(detection.get("QID")))
            elif isinstance(detection_list, dict) and detection_list.get("QID"):
                quids.append(str(detection_list.get("QID")))

        return quids
