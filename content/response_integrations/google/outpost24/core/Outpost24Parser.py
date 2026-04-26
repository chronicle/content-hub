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
from collections import Counter


class Outpost24Parser:

    @staticmethod
    def build_entity_object(raw_data):

        return EntityObject(
            raw_data=raw_data,
            hostname=raw_data.get("hostname"),
            ip=raw_data.get("ip"),
            exposed=raw_data.get("exposed"),
            created=raw_data.get("created"),
            first_seen=raw_data.get("firstSeen"),
            source=raw_data.get("source"),
            criticality=raw_data.get("businessCriticality"),
            id=raw_data.get("id"),
        )

    @staticmethod
    def find_ip_address(raw_data, entity_identifier):

        for ip_address in raw_data:
            if ip_address.get("ip") == entity_identifier:
                return ip_address

    @staticmethod
    def filter_found_information(data, risk_level_filter):

        filtered_results = []
        for information in data:
            if information.get("riskLevel").lower() in risk_level_filter:
                filtered_results.append(information)

        return filtered_results

    @staticmethod
    def add_findings_to_entity_object(entity_object, data):

        type_counter = Counter([finding["type"] for finding in data])
        risk_level_counter = Counter([finding["riskLevel"] for finding in data])

        count_initial_findings = risk_level_counter["Initial"]
        count_medium_findings = risk_level_counter["Medium"]
        count_low_findings = risk_level_counter["Low"]
        count_recommendation_findings = risk_level_counter["Recommendation"]
        count_high_findings = risk_level_counter["High"]
        count_critical_findings = risk_level_counter["Critical"]
        count_information_findings = type_counter["Information"]
        count_vulnerability_findings = type_counter["Vulnerability"]

        entity_object.set_findings_parameters(
            findings_raw_data=data,
            count_initial_findings=count_initial_findings,
            count_recommendation_findings=count_recommendation_findings,
            count_low_findings=count_low_findings,
            count_medium_findings=count_medium_findings,
            count_high_findings=count_high_findings,
            count_critical_findings=count_critical_findings,
            count_information_findings=count_information_findings,
            count_vulnerability_findings=count_vulnerability_findings,
        )

    def build_findings_list(self, raw_data):
        return [self.build_finding_object(item) for item in raw_data]

    def build_finding_object(self, raw_data):
        return Finding(
            raw_data=raw_data,
            id=raw_data.get("id"),
            name=raw_data.get("name"),
            data=raw_data.get("data"),
            description=raw_data.get("description"),
            risk_level=raw_data.get("riskLevel"),
            type=raw_data.get("type"),
            last_seen=raw_data.get("lastSeen"),
            product_name=raw_data.get("productName"),
        )
