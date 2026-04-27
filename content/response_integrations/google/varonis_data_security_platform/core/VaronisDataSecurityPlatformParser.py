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
