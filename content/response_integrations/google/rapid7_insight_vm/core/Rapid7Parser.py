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


class Rapid7Parser:
    def build_asset_object(self, raw_data):
        return Asset(raw_data=raw_data, id=raw_data.get("id"), ip=raw_data.get("ip"))

    def build_vulnerability_object(self, raw_data):
        return Vulnerability(
            raw_data=raw_data, id=raw_data.get("id"), since=raw_data.get("since")
        )

    def build_vulnerability_details_object(self, raw_data):
        return VulnerabilityDetails(
            raw_data=raw_data,
            id=raw_data.get("id"),
            title=raw_data.get("title"),
            severity=raw_data.get("severity"),
        )
