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


class FireEyeETPParser:
    def build_first_alert(self, raw_data, timezone_offset=None):
        data_json = raw_data.get("data", [])
        if data_json:
            return self.build_siemplify_alert_obj(
                alert_data=data_json[0], timezone_offset=timezone_offset
            )

    def build_alerts_array(self, raw_json, timezone_offset=None):
        alerts_data = raw_json.get("data", []) if raw_json.get("data", []) else []
        return [
            self.build_siemplify_alert_obj(
                alert_data=alert_data, timezone_offset=timezone_offset
            )
            for alert_data in alerts_data
        ]

    def build_siemplify_alert_obj(self, alert_data, timezone_offset=None):
        return Alert(
            raw_data=alert_data,
            id=alert_data.get("id"),
            timestamp=alert_data.get("attributes", {})
            .get("email", {})
            .get("timestamp", {})
            .get("accepted"),
            severity=alert_data.get("attributes", {}).get("alert", {}).get("severity"),
            etp_message_id=alert_data.get("attributes", {})
            .get("email", {})
            .get("etp_message_id"),
            malwares=alert_data.get("attributes", {})
            .get("alert", {})
            .get("explanation", {})
            .get("malware_detected", {})
            .get("malware", []),
            recipients=alert_data.get("attributes", {})
            .get("email", {})
            .get("smtp", {})
            .get("rcpt_to", "")
            .split(),
            timezone_offset=timezone_offset,
        )
