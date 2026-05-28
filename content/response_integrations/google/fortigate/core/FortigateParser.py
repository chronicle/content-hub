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


class FortigateParser:
    def build_policy_objects(self, raw_data):
        return [self.build_policy_object(item) for item in raw_data.get("results", [])]

    @staticmethod
    def build_policy_object(raw_data):
        return Policy(
            raw_data=raw_data,
            id=raw_data.get("policyid"),
            name=raw_data.get("name"),
            dst_items=raw_data.get("dstaddr", []),
            src_items=raw_data.get("srcaddr", []),
            dst_intf=raw_data.get("dstintf", []),
            src_intf=raw_data.get("srcintf", []),
            action=raw_data.get("action"),
            status=raw_data.get("status"),
        )

    def build_entity_objects(self, raw_data):
        return [self.build_entity_object(item) for item in raw_data.get("results", [])]

    @staticmethod
    def build_entity_object(raw_data):
        return Entity(raw_data=raw_data)

    def build_address_group_objects(self, raw_data):
        return [
            self.build_address_group_object(item)
            for item in raw_data.get("results", [])
        ]

    @staticmethod
    def build_address_group_object(raw_data):
        return AddressGroup(
            raw_data=raw_data,
            id=raw_data.get("addrgrpid"),
            name=raw_data.get("name"),
            items=raw_data.get("member", []),
            type=raw_data.get("type"),
            category=raw_data.get("category"),
            comment=raw_data.get("comment"),
        )

    def build_threat_log_objects(self, raw_data):
        return [
            self.build_threat_log_object(item) for item in raw_data.get("results", [])
        ]

    @staticmethod
    def build_threat_log_object(raw_data):
        return ThreatLog(
            raw_data=raw_data,
            id=raw_data.get("_metadata", {}).get("#"),
            msg=raw_data.get("msg"),
            level=raw_data.get("level"),
            subtype=raw_data.get("subtype"),
            event_time=raw_data.get("eventtime"),
            event_type=raw_data.get("eventtype"),
            timestamp=raw_data.get("_metadata", {}).get("timestamp"),
        )
