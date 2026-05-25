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
from .StellarCyberStarlightConstants import TIMESTAMP_FIELD_DEFAULT_VALUE


class StellarCyberStarlightParser:
    def build_all_hits(self, raw_data):
        return [
            self.build_hit_object(hit_json=hit_json)
            for hit_json in raw_data.get("hits", {}).get("hits", [])
        ]

    def build_hit_object(self, hit_json):
        return Hit(raw_data=hit_json)

    def build_errors(self, raw_data):
        errors = raw_data.get("error", {}).get("root_cause", [])
        if errors:
            return "\n".join(
                [self.build_error_object(error_json).message for error_json in errors]
            )

    def build_error_object(self, raw_data):
        return ErrorObject(raw_data=raw_data, message=raw_data.get("reason"))

    def build_alert_object(
        self, alert_json, timestamp_field=TIMESTAMP_FIELD_DEFAULT_VALUE
    ):
        return Alert(
            raw_data=alert_json,
            id=alert_json.get("_id"),
            event_category=alert_json.get("_source", {}).get("event_category"),
            event_name=alert_json.get("_source", {}).get("event_name"),
            severity=alert_json.get("_source", {}).get("event_score"),
            timestamp=alert_json.get("_source", {}).get(timestamp_field),
            xdr_event_name=alert_json.get("_source", {})
            .get("xdr_event", {})
            .get("name"),
        )

    def get_access_token(self, json):
        return json.get("access_token", {})
