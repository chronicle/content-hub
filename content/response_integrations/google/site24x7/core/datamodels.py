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
import hashlib
import json
import uuid
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import (
    ALERT_TYPE_MAP,
    SEVERITY_MAP,
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    DOWN_STATUS,
    UP_STATUS,
    CRITICAL_STATUS,
    TROUBLE_STATUS,
)
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time


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


class AlertLog(BaseModel):
    def __init__(self, raw_data, msg, sent_time, alert_type):
        super(AlertLog, self).__init__(raw_data)
        self.id = hashlib.sha1(json.dumps(raw_data).encode("utf-8")).hexdigest()
        self.msg = msg
        self.sent_time = sent_time
        self.alert_type = alert_type
        self.status = next(
            (
                status
                for status in [DOWN_STATUS, UP_STATUS, CRITICAL_STATUS, TROUBLE_STATUS]
                if status in msg.split()
            ),
            None,
        )

    def get_alert_info(
        self, alert_info, environment_common, device_product_field, monitors
    ):
        alert_info.events = [self.as_event(monitors)]
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.to_json())
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.msg
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.get_severity()
        alert_info.rule_generator = DEVICE_VENDOR
        alert_info.start_time = convert_string_to_unix_time(self.sent_time)
        alert_info.end_time = convert_string_to_unix_time(self.sent_time)

        return alert_info

    def get_severity(self):
        return SEVERITY_MAP.get(self.status, -1)

    def as_event(self, monitors):
        event_data = self.raw_data
        event_data["alert_type"] = ALERT_TYPE_MAP.get(self.alert_type)
        event_data["status"] = self.status
        extracted_entity = next(
            (monitor for monitor in monitors if monitor in self.msg.split()), None
        )
        if extracted_entity:
            event_data["extracted_entity"] = extracted_entity
        return dict_to_flat(event_data)


class Monitor(BaseModel):
    def __init__(self, raw_data, display_name):
        super(Monitor, self).__init__(raw_data)
        self.display_name = display_name
