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


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class DataGroup(BaseModel):
    def __init__(self, raw_data, name, type, records):
        super(DataGroup, self).__init__(raw_data)
        self.name = name
        self.type = type
        self.records = records

    def to_csv(self):
        return dict_to_flat(
            {
                "Name": self.name,
                "Type": self.type,
                "Number of records": len(self.records),
            }
        )


class PortList(BaseModel):
    def __init__(self, raw_data, name, ports):
        super(PortList, self).__init__(raw_data)
        self.name = name
        self.ports = ports

    def to_csv(self):
        return dict_to_flat({"Name": self.name, "Number of Ports": len(self.ports)})


class AddressList(BaseModel):
    def __init__(self, raw_data, name, addresses):
        super(AddressList, self).__init__(raw_data)
        self.name = name
        self.addresses = addresses

    def to_csv(self):
        return dict_to_flat(
            {"Name": self.name, "Number of Addresses": len(self.addresses)}
        )


class IRulesList(BaseModel):
    def __init__(self, raw_data, name, rule):
        super(IRulesList, self).__init__(raw_data)
        self.name = name
        self.rule = rule

    def to_csv(self):
        return dict_to_flat({"Name": self.name, "Rule": self.rule})
