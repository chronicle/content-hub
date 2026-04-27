from __future__ import annotations
import uuid
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    SEVERITY_MAP,
    HOST_GROUPING,
    DETECTION_GROUPING,
    NONE_GROUPING,
    RULE_GENERATOR,
    ENRICHMENT_INSIGHT_TEMPLATE,
    LIST_ENDPOINT_DETECTIONS_INSIGHT_TEMPLATE,
    SEVERITY_COLOR_MAP,
    DETECTION_SEVERITY_MAP,
    DEFAULT_SEVERITY,
)
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


class Detection(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        dns_name,
        ip_address,
        result,
        severity,
        first_found_datetime,
        status,
        port,
        detection_type,
        host_id,
    ):
        super(Detection, self).__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = id
        self.dns_name = (dns_name,)
        self.ip_address = ip_address
        self.result = result
        self.severity = DEFAULT_SEVERITY if severity is None else int(severity)
        self.first_found_datetime = first_found_datetime
        self.status = status
        self.port = port
        self.detection_type = detection_type
        self.host_id = host_id
        self.entry = f"{id}-{port}" if port else id

    def get_alert_info(
        self,
        alert_info,
        environment_common,
        device_product_field,
        grouping_mechanism,
        execution_time,
        detections_group,
    ):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = (
            self.id if grouping_mechanism == DETECTION_GROUPING else str(self.uuid)
        )
        alert_info.display_id = str(self.uuid)
        alert_info.name = (
            f"{self.ip_address or self.dns_name}: New Vulnerabilities Found"
            if grouping_mechanism == HOST_GROUPING
            else (
                "New Vulnerability Found"
                if grouping_mechanism == DETECTION_GROUPING
                else f"{self.ip_address or self.dns_name}: New Vulnerability"
            )
        )
        if grouping_mechanism == NONE_GROUPING:
            alert_info.description = self.result
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity(detections_group)
        alert_info.rule_generator = RULE_GENERATOR
        alert_info.start_time = (
            convert_string_to_unix_time(self.first_found_datetime)
            if grouping_mechanism == NONE_GROUPING
            else execution_time
        )
        alert_info.end_time = (
            convert_string_to_unix_time(self.first_found_datetime)
            if grouping_mechanism == NONE_GROUPING
            else execution_time
        )
        alert_info.events = self.create_events(detections_group)

        return alert_info

    def to_json(self):
        self.raw_data["event_type"] = "Vulnerability"
        return self.raw_data

    def get_siemplify_severity(self, detections_group):
        return SEVERITY_MAP.get(
            max([detection.severity for detection in detections_group]), -1
        )

    def create_events(self, detections_group):
        return [dict_to_flat(detection.to_json()) for detection in detections_group]


class Host(BaseModel):
    def __init__(
        self,
        raw_data,
        ip_address,
        netbios_name,
        dns_domain,
        dns_fqdn,
        os,
        tags,
        comment,
    ):
        super(Host, self).__init__(raw_data)
        self.ip_address = ip_address if ip_address is not None else "N/A"
        self.netbios_name = netbios_name if netbios_name is not None else "N/A"
        self.dns_domain = dns_domain if dns_domain is not None else "N/A"
        self.dns_fqdn = dns_fqdn if dns_fqdn is not None else "N/A"
        self.os = os if os is not None else "N/A"
        self.tags = tags if tags is not None else "N/A"
        self.comment = comment if comment is not None else "N/A"

    def to_table(self):
        table_data_list = []
        raw_data = self.raw_data
        if type(raw_data) is list:
            raw_data = raw_data[0]

        for key, value in raw_data.items():
            if value is not None and value != "":
                if type(value) is dict:
                    for sub_key, sub_value in value.items():
                        if sub_key == "TAG":
                            if type(sub_value) is list:
                                table_data_list.append(
                                    {
                                        "Key": "TAGS",
                                        "Value": ",".join(
                                            [tag.get("NAME") for tag in sub_value]
                                        ),
                                    }
                                )
                                continue
                        table_data_list.append({"Key": sub_key, "Value": sub_value})
                    continue
                table_data_list.append({"Key": key, "Value": value})

        return table_data_list

    def to_enrichment_data(self):
        raw_data = self.raw_data
        if type(raw_data) is list:
            raw_data = raw_data[0]

        return raw_data

    def as_insight(self):
        return ENRICHMENT_INSIGHT_TEMPLATE.format(
            ip_address=self.ip_address,
            netbios_name=self.netbios_name,
            dns_domain=self.dns_domain,
            dns_fqdn=self.dns_fqdn,
            os=self.os,
            tags=self.tags,
            comment=self.comment,
        )


class EndpointDetection(BaseModel):
    def __init__(
        self,
        raw_data,
        qid,
        title,
        diagnosis,
        consequence,
        solution,
        patchable,
        category,
        criticality_level,
    ):
        super(EndpointDetection, self).__init__(raw_data)
        self.qid = qid if qid is not None else "N/A"
        self.title = title if title is not None else "N/A"
        self.diagnosis = diagnosis if diagnosis is not None else "N/A"
        self.consequence = consequence if consequence is not None else "N/A"
        self.solution = solution if solution is not None else "N/A"
        self.patchable = patchable
        self.category = category
        self.criticality_level = DETECTION_SEVERITY_MAP.get(criticality_level)

    def to_table(self):
        return {
            "QID": self.qid,
            "Title": self.title,
            "Severity": self.criticality_level,
            "Solution": self.solution,
            "Consequence": self.consequence,
            "Patchable": self.patchable,
            "Diagnosis": self.diagnosis,
            "Category": self.category,
        }

    def as_insight(self):
        return LIST_ENDPOINT_DETECTIONS_INSIGHT_TEMPLATE.format(
            qid=self.qid,
            title=self.title,
            diagnosis=self.diagnosis,
            consequence=self.consequence,
            solution=self.solution,
            color=SEVERITY_COLOR_MAP.get(self.criticality_level),
            criticality_level=self.criticality_level,
        )
