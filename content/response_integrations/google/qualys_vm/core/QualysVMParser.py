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

    def build_detection_object(self, raw_data):
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

    def build_host_object(self, raw_data):
        host_data = raw_data
        os = None

        if type(host_data) is list:
            raw_data = [host for host in host_data]

            for host in host_data:
                if host.get("OS") is not None:
                    os = host.get("OS")
            host_data = host_data[0]

        else:
            raw_data = host_data
            os = host_data.get("OS")

        tags = None

        if host_data.get("TAGS", {}) is not None:
            all_tags = host_data.get("TAGS", {}).get("TAG", {})
            if type(all_tags) is list:
                tags = [tag.get("NAME") for tag in all_tags]
                tags = ",".join(tags)
            else:
                tags = all_tags.get("NAME")

        return Host(
            raw_data=raw_data,
            ip_address=host_data.get("IP"),
            netbios_name=host_data.get("NETBIOS"),
            dns_domain=host_data.get("DNS_DATA", {}).get("DOMAIN"),
            dns_fqdn=host_data.get("DNS_DATA", {}).get("FQDN"),
            os=os,
            tags=tags,
            comment=host_data.get("COMMENTS"),
        )

    def _get_hosts_list(self, raw_data) -> list[dict]:
        if not raw_data:
            return []

        hosts_list = []
        if isinstance(raw_data, dict):
            host_data = raw_data.get("HOST")
            if isinstance(host_data, list):
                hosts_list.extend(host_data)
            elif isinstance(host_data, dict):
                hosts_list.append(host_data)

        elif isinstance(raw_data, list):
            for item in raw_data:
                if isinstance(item, dict):
                    if "HOST" in item:
                        sub_host = item.get("HOST")
                        if isinstance(sub_host, list):
                            hosts_list.extend(sub_host)
                        elif isinstance(sub_host, dict):
                            hosts_list.append(sub_host)
                    else:
                        hosts_list.append(item)

        return hosts_list

    def filter_hostname(self, raw_data, hostname):
        hosts_list = self._get_hosts_list(raw_data)
        hostname_data = []
        for host_data in hosts_list:
            netbios = host_data.get("NETBIOS")
            dns_hostname = host_data.get("DNS_DATA", {}).get("HOSTNAME")
            if netbios == hostname or dns_hostname == hostname:
                hostname_data.append(host_data)

        if len(hostname_data) == 1:
            return hostname_data[0]
        return hostname_data

    def get_ip_for_hostname(self, raw_data, hostname):
        hosts_list = self._get_hosts_list(raw_data)
        for host_data in hosts_list:
            netbios = host_data.get("NETBIOS")
            dns_hostname = host_data.get("DNS_DATA", {}).get("HOSTNAME")
            if netbios == hostname or dns_hostname == hostname:
                return host_data.get("IP")

        return None

    def build_endpointdetection_object(self, raw_data):

        vulnerabilities = raw_data.get("VULN_LIST").get("VULN")
        if type(vulnerabilities) is dict:
            return [
                EndpointDetection(
                    raw_data=vulnerabilities,
                    qid=vulnerabilities.get("QID"),
                    title=vulnerabilities.get("TITLE", {}),
                    diagnosis=vulnerabilities.get("DIAGNOSIS", {}),
                    consequence=vulnerabilities.get("CONSEQUENCE", {}),
                    solution=vulnerabilities.get("SOLUTION", {}),
                    patchable=vulnerabilities.get("PATCHABLE", {}),
                    category=vulnerabilities.get("CATEGORY", {}),
                    criticality_level=vulnerabilities.get("SEVERITY_LEVEL"),
                )
            ]

        elif type(vulnerabilities) is list:
            return [
                EndpointDetection(
                    raw_data=vulnerability,
                    qid=vulnerability.get("QID"),
                    title=vulnerability.get("TITLE", {}),
                    diagnosis=vulnerability.get("DIAGNOSIS", {}),
                    consequence=vulnerability.get("CONSEQUENCE", {}),
                    solution=vulnerability.get("SOLUTION", {}),
                    patchable=vulnerability.get("PATCHABLE", {}),
                    category=vulnerability.get("CATEGORY", {}),
                    criticality_level=vulnerability.get("SEVERITY_LEVEL"),
                )
                for vulnerability in vulnerabilities
            ]
        else:
            return []

    def get_detection_quids(self, raw_data):
        quids = []
        hosts_list = self._get_hosts_list(raw_data)
        for host_data in hosts_list:
            detection_list = host_data.get("DETECTION_LIST", {}).get("DETECTION")
            if not detection_list:
                continue
            if isinstance(detection_list, list):
                for detection in detection_list:
                    quids.append(detection.get("QID"))
            elif isinstance(detection_list, dict):
                quids.append(detection_list.get("QID"))

        return quids
