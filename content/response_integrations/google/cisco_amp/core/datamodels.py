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
import uuid

from TIPCommon import dict_to_flat

from .consts import DEVICE_VENDOR, DEVICE_PRODUCT, SEVERITY_TO_SIEM


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def is_empty(self):
        return not bool(self.raw_data)

    def to_event(self):
        return dict_to_flat(self.raw_data)


class Event(BaseModel):
    """
    Cisco AMP Event
    """

    def __init__(
        self,
        raw_data,
        severity=None,
        event_id=None,
        event_type=None,
        start_date=None,
        timestamp=None,
        timestamp_nanoseconds=None,
    ):
        super(Event, self).__init__(raw_data)
        self.id = event_id
        self.severity = severity
        self.event_type = event_type
        self.start_date = start_date
        self.uuid = uuid.uuid4()
        self.timestamp = timestamp
        self.timestamp_nanoseconds = timestamp_nanoseconds

        try:
            self.timestamp_ms = int(
                (float(timestamp) + (float(timestamp_nanoseconds) / float(1000000000)))
                * 1000
            )
        except Exception:
            try:
                self.timestamp_ms = self.timestamp * 1000
            except Exception:
                self.timestamp_ms = 1

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(self.to_flat())
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = self.event_type
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.to_flat().get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.event_type
        alert_info.start_time = self.timestamp_ms
        alert_info.end_time = self.timestamp_ms
        alert_info.events = [self.to_event()]

        return alert_info

    def get_siemplify_severity(self):
        if (not self.severity) or (not SEVERITY_TO_SIEM.get(self.severity)):
            return SEVERITY_TO_SIEM["Info"]
        return SEVERITY_TO_SIEM.get(self.severity)

    def to_event(self):
        raw_data = copy.deepcopy(self.raw_data)
        raw_data.update({"timestamp": self.timestamp_ms})
        return dict_to_flat(raw_data)
