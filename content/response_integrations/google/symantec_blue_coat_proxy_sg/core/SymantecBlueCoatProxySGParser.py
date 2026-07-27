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
from soar_sdk.SiemplifyDataModel import EntityTypes


class SymantecBlueCoatProxySGParser:
    @staticmethod
    def build_entity_info_object(raw_data, raw_json_data, entity_type):
        if entity_type == EntityTypes.HOSTNAME:
            return HostnameEntityInfo(
                raw_data=raw_data,
                raw_json_data=raw_json_data,
                official_hostname=raw_json_data.get("Official Host Name"),
                resolved_addresses=raw_json_data.get("Resolved Addresses"),
                cache_ttl=raw_json_data.get("Cache TTL"),
                error=raw_json_data.get("Error"),
            )

        if entity_type == EntityTypes.ADDRESS:
            return IpEntityInfo(
                raw_data=raw_data,
                raw_json_data=raw_json_data,
                country=raw_json_data.get("Country"),
            )

        if entity_type == EntityTypes.URL:
            category_groups = raw_json_data.get("category groups")
            if category_groups is None:
                category_group = raw_json_data.get("category group")
            else:
                category_group = category_groups
            return UrlEntityInfo(
                raw_data=raw_data,
                raw_json_data=raw_json_data,
                risk_level=raw_json_data.get("risk level"),
                categories=raw_json_data.get("% categories"),
                category_group=category_group,
            )
