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

    def filter_hostname(self, raw_data, hostname):
        raw_host_data = raw_data.get("HOST")
        hostname_data = None
        if type(raw_host_data) is dict:
            if raw_host_data.get("NETBIOS") == hostname:
                return raw_host_data
        else:
            hostname_data = []
            for host_data in raw_host_data:
                if host_data.get("NETBIOS") == hostname:
                    hostname_data.append(host_data)
            return hostname_data

        return hostname_data

    def get_ip_for_hostname(self, raw_data, hostname):
        raw_host_data = raw_data.get("HOST")
        hostname_data = None
        for host_data in raw_host_data:
            if host_data.get("NETBIOS") == hostname:
                return host_data.get("IP")

        return hostname_data

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
        if type(raw_data) is list and len(raw_data) == 0:
            return quids

        raw_host_data = raw_data.get("HOST")
        quids = []
        detection_list = raw_host_data.get("DETECTION_LIST").get("DETECTION")
        if type(detection_list) is list:
            for detection in detection_list:
                quids.append(detection.get("QID"))

        elif type(detection_list) is dict:
            quids.append(detection_list.get("QID"))

        return quids
