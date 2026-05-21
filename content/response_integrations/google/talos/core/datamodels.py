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
from .constants import REPUTATION_TYPE_MAPPING
from .UtilsManager import convert_list_to_comma_string


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


class WhoisReport(BaseModel):
    def __init__(self, raw_data):
        super(WhoisReport, self).__init__(raw_data)


class Reputation(BaseModel):
    def __init__(self, raw_data, reputation_type):
        super(Reputation, self).__init__(raw_data)
        self.reputation_type = reputation_type
        self.reputation = self.raw_data.get("reputation", {})

    def to_enrichment_data(self, prefix=None):
        data = {}
        host_info = self.raw_data.get("volume_info", {}).get("host_info", {}) or {}

        if self.reputation_type == REPUTATION_TYPE_MAPPING.get("ip"):
            geo_location = self.reputation.get("geo_location", {}) or {}
            org_stats = self.reputation.get("org_stats", {}) or {}

            data = {
                "geo_location": f"{geo_location.get('locality', '')} "
                f"{geo_location.get('state_or_province', '')}"
                f"{geo_location.get('postal_code', '')}"
                f"{geo_location.get('country', '')}",
                "org_name": org_stats.get("org_info", {}).get("org_name", ""),
                "hostname": self.reputation.get("hostname", ""),
                "threat_level": self.reputation.get("threat_level_mnemonic", ""),
                "spam_level": self.reputation.get("spam_level", ""),
                "first_occurence": org_stats.get("first_occurence", ""),
            }
        elif self.reputation_type == REPUTATION_TYPE_MAPPING.get("hostname"):
            data = {
                "geo_country": convert_list_to_comma_string(
                    [
                        item.get("geo_location", {}).get("country", "")
                        for item in self.raw_data.get("location_detail", {}).get(
                            "location_info", []
                        )
                    ]
                ),
                "org_name": self.raw_data.get("info", {})
                .get("org_info", {})
                .get("org_name", ""),
                "hostname": host_info.get("hostname", ""),
            }
        elif self.reputation_type == REPUTATION_TYPE_MAPPING.get("domain"):
            data = {
                "geo_country": convert_list_to_comma_string(
                    [
                        item.get("geo_location", {}).get("country", "")
                        for item in self.raw_data.get("location_detail", {}).get(
                            "location_info", []
                        )
                    ]
                ),
                "org_name": self.raw_data.get("info", {})
                .get("org_stats", {})
                .get("org_info", {})
                .get("org_name", ""),
                "hostname": host_info.get("hostname", ""),
                "first_occurence": self.raw_data.get("firstoccurence", ""),
            }
        elif self.reputation_type == REPUTATION_TYPE_MAPPING.get("domain_url"):
            data = {"threat_reputation": self.reputation}
        data = dict_to_flat(
            {key: value for key, value in data.items() if str(value).strip()}
        )
        return add_prefix_to_dict(data, prefix) if prefix else data
