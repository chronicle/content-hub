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
import copy
from TIPCommon import dict_to_flat, add_prefix_to_dict


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Report(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.event_logs = []
        self.suspicious_objects = []
        self.screenshot = None

    def to_json(self):
        data = copy.deepcopy(self.raw_data)

        data.update(
            {
                "EventLogs": [event_log.to_json() for event_log in self.event_logs],
                "SuspiciousObjects": [
                    suspicious_object.to_json()
                    for suspicious_object in self.suspicious_objects
                ],
                "Screenshot": self.screenshot,
            }
        )

        return data


class EventLog(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)


class SuspiciousObject(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)
