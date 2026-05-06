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


class Site24x7Parser:
    def build_alert_logs_list(self, raw_data):
        return [
            self.build_alert_log_object(raw_data=alert_log)
            for alert_log in raw_data.get("data", [])
        ]

    def build_alert_log_object(self, raw_data):
        return AlertLog(
            raw_data=raw_data,
            msg=raw_data.get("msg"),
            sent_time=raw_data.get("sent_time"),
            alert_type=raw_data.get("alert_type"),
        )

    def build_monitors_list(self, raw_data):
        return [
            self.build_monitor_object(raw_data=monitor)
            for monitor in raw_data.get("data", [])
        ]

    def build_monitor_object(self, raw_data):
        return Monitor(raw_data=raw_data, display_name=raw_data.get("display_name"))
