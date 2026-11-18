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
from .UtilsManager import convert_list_to_comma_string


class SymantecESCCParser:

    def build_list_of_device_groups(self, raw_json):
        raw_data = raw_json.get("device_groups", [])
        return [self.build_device_group_obj(item) for item in raw_data]

    def build_device_group_obj(self, raw_json):
        return DeviceGroup(
            raw_data=raw_json, id=raw_json.get("id"), name=raw_json.get("name")
        )

    def build_list_of_devices(self, raw_json):
        raw_data = raw_json.get("devices", [])
        return [self.build_device_obj(item) for item in raw_data]

    def build_device_obj(self, raw_json):
        return Device(
            raw_data=raw_json,
            id=raw_json.get("id"),
            name=raw_json.get("name"),
            os_name=raw_json.get("os", {}).get("name"),
            host=raw_json.get("host"),
            domain=raw_json.get("domain"),
            adapters=raw_json.get("adapters"),
            device_status=raw_json.get("device_status"),
            user=raw_json.get("os", {}).get("user"),
        )

    def build_entity_details_obj(self, raw_json):
        return EntityDetails(
            raw_data=raw_json,
            reputation=raw_json.get("reputation", ""),
            prevalence=raw_json.get("prevalence"),
            top_countries=convert_list_to_comma_string(
                [
                    country
                    for country in raw_json.get("targetOrgs", {}).get(
                        "topCountries", []
                    )
                ]
            ),
            top_industries=convert_list_to_comma_string(
                [
                    industry
                    for industry in raw_json.get("targetOrgs", {}).get(
                        "topIndustries", []
                    )
                ]
            ),
            first_seen=raw_json.get("firstSeen"),
            last_seen=raw_json.get("lastSeen"),
            state=raw_json.get("state"),
        )

    def build_list_of_related_iocs(self, raw_json):
        raw_data = raw_json.get("related", [])
        return [self.build_related_ioc_obj(item) for item in raw_data]

    def build_related_ioc_obj(self, raw_json):
        return RelatedIOC(
            raw_data=raw_json,
            ioc_type=raw_json.get("iocType"),
            relation=raw_json.get("relation"),
            ioc_values=raw_json.get("iocValues", []),
        )
