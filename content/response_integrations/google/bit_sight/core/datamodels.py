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
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_MAPPING, TIME_FORMAT
from datetime import datetime
import copy


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        alert_id,
        trigger,
        severity,
        alert_type,
        alert_date,
        company_id,
        message,
    ):
        super(Alert, self).__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.alert_id = alert_id
        self.trigger = trigger
        self.severity = severity
        self.alert_type = alert_type
        self.alert_date = alert_date
        self.alert_date_ms = convert_string_to_unix_time(self.alert_date + "T00:00:00Z")
        self.company_id = company_id
        self.message = message
        self.findings = []

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.alert_id
        alert_info.display_id = f"{DEVICE_VENDOR}_{self.alert_id}"
        alert_info.name = self.trigger
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.flat_raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.alert_type
        alert_info.source_grouping_identifier = self.alert_type
        alert_info.start_time = self.alert_date_ms
        alert_info.end_time = self.alert_date_ms
        alert_info.events = self.to_events()

        return alert_info

    def get_siemplify_severity(self):
        return SEVERITY_MAPPING.get(self.severity, -1)

    def to_events(self):
        event_data = copy.deepcopy(self.raw_data)
        event_data["siemplify_type"] = "Alert"
        events = [dict_to_flat(event_data)]
        for finding in self.findings:
            events.extend(finding.to_events())
        return events


class Finding(BaseModel):
    def __init__(self, raw_data):
        super(Finding, self).__init__(raw_data)

    def to_events(self):
        events = []
        main_data = copy.deepcopy(self.raw_data)
        main_data["siemplify_type"] = "Finding"
        main_data.pop("related_findings", None)
        assets = main_data.pop("assets", None)
        for asset in assets:
            event_data = copy.deepcopy(main_data)
            asset_key = "asset_ip" if asset.get("is_ip", False) else "asset_domain"
            asset[asset_key] = asset.get("asset")
            event_data["assets"] = asset
            events.append(dict_to_flat(event_data))
        return events


class Company(BaseModel):
    def __init__(
        self,
        raw_data,
        guid,
        name,
        description,
        industry,
        sub_industry,
        certifications,
        display_url,
        rating,
    ):
        super(Company, self).__init__(raw_data)
        self.guid = guid
        self.name = name
        self.description = description
        self.industry = industry
        self.sub_industry = sub_industry
        self.certifications = certifications
        self.display_url = display_url
        self.rating = rating

    def to_csv(self):
        return {
            "Name": self.name,
            "Description": self.description,
            "Industry": self.industry,
            "Sub Industry": self.sub_industry,
            "Certification": self.certifications,
            "Rating": self.rating,
        }

    def to_json(self):
        json_data = copy.deepcopy(self.raw_data)
        json_data["rating"] = self.rating
        return json_data


class VulnerabilityStats(BaseModel):
    def __init__(self, raw_data, start_date, end_date, vulnerabilities):
        super(VulnerabilityStats, self).__init__(raw_data)
        self.start_date = datetime.strptime(start_date, TIME_FORMAT)
        self.end_date = datetime.strptime(end_date, TIME_FORMAT)
        self.vulnerabilities = vulnerabilities

    def to_json(self):
        return [vulnerability.to_json() for vulnerability in self.vulnerabilities]


class Vulnerability(BaseModel):
    def __init__(
        self, raw_data, id, name, first_seen, event_count, host_count, confidence
    ):
        super(Vulnerability, self).__init__(raw_data)
        self.id = id
        self.name = name
        self.first_seen = first_seen
        self.event_count = event_count
        self.host_count = host_count
        self.confidence = confidence

    def to_json(self):
        json_data = copy.deepcopy(self.raw_data)
        json_data.pop("severity", None)
        json_data.pop("severity_category", None)
        return json_data

    def to_csv(self):
        return {
            "ID": self.id,
            "Name": self.name,
            "First Seen": self.first_seen,
            "Event Count": self.event_count,
            "Affected Hosts": self.host_count,
            "Confidence": self.confidence,
        }


class Highlight(BaseModel):
    def __init__(self, raw_data):
        super(Highlight, self).__init__(raw_data)
