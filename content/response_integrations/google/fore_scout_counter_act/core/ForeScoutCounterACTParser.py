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
from .datamodels import EndpointInfo


class ForeScoutCounterACTParser:
    """
    ForeScout CounterACT Parsing layer
    """

    @staticmethod
    def build_endpoint_info_obj(raw_data):
        return EndpointInfo(
            raw_data=raw_data,
            ip_address=raw_data.get("host", {}).get("ip"),
            mac_address=raw_data.get("host", {}).get("mac"),
            onsite=raw_data.get("host", {})
            .get("fields", {})
            .get("onsite", {})
            .get("value"),
            guest_corporate_state=raw_data.get("host", {})
            .get("fields", {})
            .get("guest_corporate_state", {})
            .get("value"),
            fingerprint=raw_data.get("host", {})
            .get("fields", {})
            .get("fingerprint", {})
            .get("value"),
            vendor=raw_data.get("host", {})
            .get("fields", {})
            .get("vendor", {})
            .get("value"),
            classification=raw_data.get("host", {})
            .get("fields", {})
            .get("prim_classification", {})
            .get("value"),
            agent_version=raw_data.get("host", {})
            .get("fields", {})
            .get("agent_version", {})
            .get("value"),
            online=raw_data.get("host", {})
            .get("fields", {})
            .get("online", {})
            .get("value"),
        )
