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


class CiscoOrbitalParser:
    def get_auth_token(self, raw_json):
        return raw_json.get("token")

    def get_job_id(self, raw_json):
        return raw_json.get("ID")

    def get_endpoints_results(self, raw_json, limit):
        return [
            EndpointResult(
                raw_data=result,
                hostname=result.get("hostinfo", {}).get("hostname"),
                local_ipv4=self.get_local_ips(result, "ipv4"),
                local_ipv6=self.get_local_ips(result, "ipv6"),
                external_ipv4=result.get("hostinfo", {})
                .get("external", {})
                .get("ipv4"),
                error=",".join(
                    [
                        item.get("error")
                        for item in result.get("osQueryResult", [])
                        if item.get("error", "").strip()
                    ]
                ),
                tables_data=self.get_tables_data(result.get("osQueryResult", [])),
                limit=limit,
            )
            for result in raw_json.get("results", []) or []
        ]

    def get_tables_data(self, results):
        return [
            TableData(
                columns=result.get("columns", []), values=result.get("values", [])
            )
            for result in results
        ]

    def get_local_ips(self, result, key):
        return [
            value.get(key)
            for value in result.get("hostinfo", {}).get("interfaces", {}).values()
            if value.get(key)
        ]
