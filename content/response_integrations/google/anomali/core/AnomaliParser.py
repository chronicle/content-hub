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


class AnomaliParser:
    def build_results(self, raw_json, method, pure_data=False, limit=None, *kwargs):
        return [
            getattr(self, method)(item_json, *kwargs)
            for item_json in (raw_json if pure_data else raw_json.get("objects", []))[
                :limit
            ]
        ]

    def build_result(self, raw_json, method, *kwargs):
        return getattr(self, method)(raw_json.get("objects", {}), *kwargs)

    @staticmethod
    def build_threat(raw_json):
        return Threat(
            raw_data=raw_json,
            threat_id=raw_json.get("id"),
            severity=raw_json.get("meta", {}).get("severity"),
            names=(
                [tag.get("name", "") for tag in raw_json.get("tags", [])]
                if raw_json.get("tags")
                else ""
            ),
            **raw_json
        )

    @staticmethod
    def get_next_cursor(raw_json):
        return raw_json.get("meta", {}).get("next")

    @staticmethod
    def build_indicator_object(raw_json):
        return Indicator(raw_json, **raw_json)

    @staticmethod
    def build_association_object(raw_json):
        return Associations(raw_json, **raw_json)

    @staticmethod
    def build_association_details_object(raw_json):
        if isinstance(raw_json.get("status", {}), dict):
            status_display_name = raw_json.get("status", {}).get("display_name", "")
        else:
            status_display_name = raw_json.get("status", "")

        return AssociationDetails(
            raw_data=raw_json, status_display_name=status_display_name, **raw_json
        )
