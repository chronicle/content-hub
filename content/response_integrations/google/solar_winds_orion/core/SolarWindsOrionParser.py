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


class SolarWindsOrionParser:
    def build_all_query_results(self, raw_data):
        return [
            self.build_query_result_object(result_json=result_json)
            for result_json in raw_data.get("results", [])
        ]

    def build_query_result_object(self, result_json):
        return QueryResult(
            raw_data=result_json,
            ip_address=result_json.get("IpAddress"),
            display_name=result_json.get("DisplayName"),
        )

    def build_error_object(self, raw_data):
        return ErrorObject(raw_data=raw_data, message=raw_data.get("Message"))
