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


class TenableParser:
    def get_asset_id(self, raw_data, asset_name):
        assets = raw_data.get("response", {}).get("usable", [])
        return next(
            (
                asset.get("id", "")
                for asset in assets
                if asset.get("name", "") == asset_name
            ),
            "",
        )

    def build_scan_object(self, raw_data):
        response = raw_data.get("response")

        return Scan(raw_data=response)

    def build_ip_list_asset(self, raw_data):
        raw_json = raw_data.get("response")

        return IPListAsset(
            raw_data=raw_json,
            defined_ips=raw_json.get("typeFields", {}).get("definedIPs"),
        )

    def build_ip_object(self, raw_data):
        response = raw_data.get("response", {})

        return EnrichIP(raw_data=response)
