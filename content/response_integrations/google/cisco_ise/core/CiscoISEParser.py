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


class CiscoISEParser:
    def build_endpoint_groups_list(self, raw_data):
        return [
            self.build_endpoint_group_object(item)
            for item in raw_data.get("SearchResult", {}).get("resources", [])
        ]

    def build_endpoint_group_object(self, raw_data):
        return EndpointGroup(
            raw_data=raw_data,
            id=raw_data.get("id"),
            name=raw_data.get("name"),
            description=raw_data.get("description"),
        )
