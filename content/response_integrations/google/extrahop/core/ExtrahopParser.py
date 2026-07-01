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
from ..core.datamodels import *


class ExtrahopParser:
    def build_detections_list(self, raw_data):
        return [self.build_detection(item) for item in raw_data]

    def build_detection(self, raw_data):
        return Detection(
            raw_data=raw_data,
            id=f'{raw_data.get("id")}',
            title=raw_data.get("title"),
            description=raw_data.get("description"),
            risk_score=raw_data.get("risk_score"),
            type=raw_data.get("type"),
            update_time=raw_data.get("update_time"),
            participants=raw_data.get("participants", []),
        )

    def build_device(self, raw_data):
        return Device(raw_data=raw_data, id=raw_data.get("id"))
