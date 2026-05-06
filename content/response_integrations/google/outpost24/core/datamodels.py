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

import copy
import uuid

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon import add_prefix_to_dict, dict_to_flat

from .constants import (
    DEVICE_PRODUCT,
    DEVICE_VENDOR,
    INSIGHT_HTML_TEMPLATE,
    INSIGHT_HTML_TEMPLATE_FINDINGS,
    RISK_COLOR_MAP,
    SEVERITY_MAP,
)


class BaseModel:
    """Base model for inheritance"""

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.raw_data)

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class EntityObject(BaseModel):
    def __init__(
        self,
        raw_data,
        hostname,
        ip,
        exposed,
        created,
        first_seen,
        source,
        criticality,
        id,
    ):
        super().__init__(raw_data)
        self.id = id
        self.hostname = hostname
        self.ip = ip
        self.exposed = exposed
        self.created = created
        self.first_seen = first_seen
        self.source = ",".join(source)
        self.criticality = criticality
        self.count_initial_findings = None
        self.count_recommendation_findings = None
        self.count_low_findings = None
        self.count_medium_findings = None
        self.count_high_findings = None
        self.count_critical_findings = None
        self.count_information_findings = None
        self.count_vulnerability_findings = None

    def as_insight(self, return_finding_information):

        insight = INSIGHT_HTML_TEMPLATE.format(
            criticality=self.criticality,
            hostname=self.hostname,
            ip=self.ip,
            exposed=self.exposed,
            source=self.source,
            risk_color=RISK_COLOR_MAP.get(self.criticality),
        )

        if return_finding_information:

            findings_insight = INSIGHT_HTML_TEMPLATE_FINDINGS.format(
                count_vulnerability_findings=self.count_vulnerability_findings,
                count_initial_findings=self.count_initial_findings,
                count_information_findings=self.count_information_findings,
                count_recommendation_findings=self.count_recommendation_findings,
                count_low_findings=self.count_low_findings,
                count_medium_findings=self.count_medium_findings,
                count_high_findings=self.count_high_findings,
                count_critical_findings=self.count_critical_findings,
            )
            insight += findings_insight

        return insight

    def set_findings_parameters(
        self,
        findings_raw_data,
        count_initial_findings,
        count_recommendation_findings,
        count_low_findings,
        count_medium_findings,
        count_high_findings,
        count_critical_findings,
        count_information_findings,
        count_vulnerability_findings,
    ):

        self.count_initial_findings = count_initial_findings
        self.count_medium_findings = count_medium_findings
        self.count_low_findings = count_low_findings
        self.count_recommendation_findings = count_recommendation_findings
        self.count_high_findings = count_high_findings
        self.count_critical_findings = count_critical_findings
        self.count_information_findings = count_information_findings
        self.count_vulnerability_findings = count_vulnerability_findings
        self.findings_raw_data = findings_raw_data

    def to_table(self):
        table_data_list = []

        for key, value in self.raw_data.items():
            if value is not None and value != "":
                if key == "source":
                    value = ",".join(value)
                table_data_list.append({"Key": key, "Value": value})

        return table_data_list

    def to_findings_table(self):

        return [{
                    "CVE": finding.get("cve"),
                    "Product Name": finding.get("productName"),
                    "Service Name": finding.get("serviceName"),
                    "Type": finding.get("type"),
                    "Solution": finding.get("solution"),
                    "Reason": finding.get("data"),
                    "Description": finding.get("description"),
                    "Risk Level": finding.get("riskLevel"),
                } for finding in self.findings_raw_data]

    def to_enrichment_data(self, prefix=None, return_finding_information=False):

        enrichement_data = self.raw_data.copy()

        if return_finding_information:
            enrichement_data["count_initial_findings"] = self.count_initial_findings
            enrichement_data["count_low_findings"] = self.count_low_findings
            enrichement_data["count_medium_findings"] = self.count_medium_findings
            enrichement_data["count_critical_findings"] = self.count_critical_findings
            enrichement_data["count_high_findings"] = self.count_high_findings
            enrichement_data["count_recommendation_findings"] = (
                self.count_vulnerability_findings
            )

        data = dict_to_flat(enrichement_data)

        return add_prefix_to_dict(data, prefix) if prefix else data

    def to_json(self, return_finding_information=False):

        json_result = self.raw_data.copy()
        if return_finding_information:
            json_result["Findings"] = self.findings_raw_data

        return json_result


class Finding(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        name,
        data,
        description,
        risk_level,
        type,
        last_seen,
        product_name,
    ):
        super().__init__(raw_data)
        self.uuid = uuid.uuid4()
        self.id = id
        self.name = name
        self.data = data
        self.description = description
        self.risk_level = risk_level
        self.type = type
        self.last_seen = last_seen
        self.product_name = product_name

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.raw_data)
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.name
        alert_info.reason = self.data
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.type
        alert_info.start_time = alert_info.end_time = convert_string_to_unix_time(
            self.last_seen
        )
        alert_info.events = [self.as_event()]

        return alert_info

    def as_event(self):
        event_data = copy.deepcopy(self.raw_data)
        return dict_to_flat(event_data)

    def get_siemplify_severity(self):
        return SEVERITY_MAP.get(self.risk_level, -1)
