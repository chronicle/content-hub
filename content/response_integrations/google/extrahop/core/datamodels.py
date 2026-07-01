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
import dataclasses
import uuid
import copy

from TIPCommon.transformation import dict_to_flat, add_prefix_to_dict

from ..core.constants import DEVICE_VENDOR, DEVICE_PRODUCT, DEVICE_OBJECT_TYPE


@dataclasses.dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    client_id: str
    client_secret: str
    verify_ssl: bool


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


class Detection(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        title,
        description,
        risk_score,
        type,
        update_time,
        participants,
    ):
        super(Detection, self).__init__(raw_data)
        self.uuid = str(uuid.uuid4())
        self.id = id
        self.title = title
        self.description = description
        self.risk_score = risk_score
        self.type = type
        self.update_time = update_time
        self.participants = participants
        self.devices = []

    def get_alert_info(self, alert_info, environment_common, device_product_field):
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.to_json())
        )
        alert_info.ticket_id = self.id
        alert_info.display_id = self.id
        alert_info.name = self.title
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field) or DEVICE_PRODUCT
        )
        alert_info.priority = self.risk_score
        alert_info.rule_generator = self.type
        alert_info.end_time = alert_info.start_time = self.update_time
        alert_info.events = self.to_events()

        return alert_info

    def to_events(self):
        events = []
        mutable_data = copy.deepcopy(self.raw_data)
        participants = mutable_data.pop("participants", None)
        for participant in participants:
            event_data = copy.deepcopy(mutable_data)
            if participant.get("object_type", "") == DEVICE_OBJECT_TYPE:
                participant["details"] = next(
                    (
                        device.to_json()
                        for device in self.devices
                        if device.id == participant.get("object_id")
                    )
                )
            else:
                participant[participant.get("object_type", "")] = participant.get(
                    "object_value", ""
                )
            event_data.update(participant)
            events.append(dict_to_flat(event_data))
        return events


class Device(BaseModel):
    def __init__(self, raw_data, id):
        super(Device, self).__init__(raw_data)
        self.id = id
