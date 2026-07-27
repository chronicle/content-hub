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
from .datamodels import Device, Event, Process, Policy


class CBDefenseParser:
    """
    CB Defense Transformation Layer.
    """

    @staticmethod
    def build_siemplify_device_obj(device_data):
        return Device(raw_data=device_data, **device_data)

    @staticmethod
    def build_siemplify_event_obj(event_data):
        return Event(raw_data=event_data, **event_data)

    @staticmethod
    def build_siemplify_process_obj(process_data):
        return Process(raw_data=process_data, **process_data)

    @staticmethod
    def build_siemplify_policy_obj(policy_data):
        return Policy(raw_data=policy_data, **policy_data)
