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


class FireEyeNXParser:
    def build_alerts_array(self, raw_data):
        alerts_data = raw_data.get("alert", [])
        return [
            self.build_siemplify_alert_obj(alert_data=alert_data)
            for alert_data in alerts_data
        ]

    def build_siemplify_alert_obj(self, alert_data):
        return Alert(
            raw_data=alert_data,
            malwares=alert_data.get("explanation", {})
            .get("malwareDetected", {})
            .get("malware", []),
            cnc_services=alert_data.get("explanation", {})
            .get("cncServices", {})
            .get("cncService", []),
            src=alert_data.get("src", {}),
            url=alert_data.get("alertUrl"),
            action=alert_data.get("action"),
            occurred=alert_data.get("occurred"),
            attack_time=alert_data.get("attackTime"),
            dst=alert_data.get("dst", {}),
            appliance_id=alert_data.get("applianceId"),
            id=alert_data.get("id"),
            name=alert_data.get("name"),
            severity=alert_data.get("severity"),
            uuid=alert_data.get("uuid"),
            ack=alert_data.get("ack"),
            product=alert_data.get("product"),
            vlan=alert_data.get("vlan"),
            malicious=alert_data.get("malicious"),
            sc_version=alert_data.get("scVersion"),
        )
