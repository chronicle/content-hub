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
from mandiant.core.datamodels import *


class MandiantParser:
    def get_token(self, raw_json):
        return raw_json.get("access_token")

    def build_indicators_list(self, raw_data):
        return [
            self.build_indicator_obj(item) for item in raw_data.get("indicators", [])
        ]

    def build_indicator_obj(self, raw_json):
        return Indicator(raw_json, **raw_json)

    def build_actor_obj(self, raw_json):
        return ThreatActor(raw_json, **raw_json)

    def build_vulnerability_obj(self, raw_json):
        return Vulnerability(raw_json, **raw_json)

    def build_malware_obj(self, raw_json):
        return Malware(raw_json, **raw_json)
