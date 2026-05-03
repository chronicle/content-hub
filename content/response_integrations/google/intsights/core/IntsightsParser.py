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


class IntsightsParser:
    def build_iocs_object(self, raw_data):
        return Iocs(raw_data=raw_data, **raw_data)

    def build_alert_obj(self, raw_data):
        return Alert(
            raw_data=raw_data,
            network_type=raw_data.get("Details", {})
            .get("Source", {})
            .get("NetworkType"),
            alert_type=raw_data.get("Details", {}).get("Source", {}).get("Type"),
            severity=raw_data.get("Details", {}).get("Severity", {}),
            title=raw_data.get("Details", {}).get("Title"),
            **raw_data
        )
