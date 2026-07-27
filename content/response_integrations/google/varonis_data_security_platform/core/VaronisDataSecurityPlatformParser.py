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
from .VaronisDataSecurityPlatformDatamodels import Alert, Event

from typing import List, Dict, Any


class VaronisDataSecurityPlatformParser:
    def build_alert(self, alert_data: Dict[str, Any]) -> Alert:
        return Alert(alert_data)

    def build_alerts(self, alerts_data: List[Dict[str, Any]]) -> List[Alert]:
        return [self.build_alert(alert_data) for alert_data in alerts_data]

    def build_event(self, event_data: Dict[str, Any]) -> Event:
        return Event(event_data)

    def build_events(self, events_data: List[Dict[str, Any]]) -> List[Event]:
        return [self.build_event(event_data) for event_data in events_data]
