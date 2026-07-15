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


class AnomaliStaxxParser:
    def build_indicator_object(self, indicator_json, timezone_offset):
        return Indicator(
            raw_data=indicator_json,
            indicator=indicator_json.get("indicator"),
            tlp=indicator_json.get("tlp"),
            itype=indicator_json.get("itype"),
            severity=indicator_json.get("severity"),
            classification=indicator_json.get("classification"),
            detail=indicator_json.get("detail"),
            confidence=indicator_json.get("confidence"),
            actor=indicator_json.get("actor"),
            feed_name=indicator_json.get("feed_name"),
            source=indicator_json.get("source"),
            feed_site_netloc=indicator_json.get("feed_site_netloc"),
            campaign=indicator_json.get("campaign"),
            type=indicator_json.get("type"),
            id=indicator_json.get("id"),
            date_last=indicator_json.get("date_last"),
            timezone_offset=timezone_offset,
        )
