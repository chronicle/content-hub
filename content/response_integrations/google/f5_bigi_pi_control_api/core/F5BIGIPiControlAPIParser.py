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


class F5BIGIPiControlAPIParser:
    def build_data_groups_list(self, raw_data):
        return [self.build_data_group_object(item) for item in raw_data]

    def build_data_group_object(self, raw_data):
        return DataGroup(
            raw_data=raw_data,
            name=raw_data.get("name"),
            type=raw_data.get("type"),
            records=raw_data.get("records", []),
        )

    def build_port_lists_list(self, raw_data):
        return [self.build_port_list_object(item) for item in raw_data]

    def build_port_list_object(self, raw_data):
        return PortList(
            raw_data=raw_data,
            name=raw_data.get("name"),
            ports=raw_data.get("ports", []),
        )

    def build_address_lists_list(self, raw_data):
        return [self.build_address_list_object(item) for item in raw_data]

    def build_address_list_object(self, raw_data):
        return AddressList(
            raw_data=raw_data,
            name=raw_data.get("name"),
            addresses=raw_data.get("addresses", []),
        )

    def build_irules_list(self, raw_data):
        return [self.build_irule_object(item) for item in raw_data]

    def build_irule_object(self, raw_data):
        return IRulesList(
            raw_data=raw_data,
            name=raw_data.get("name"),
            rule=raw_data.get("apiAnonymous", []),
        )
