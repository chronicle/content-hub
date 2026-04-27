from __future__ import annotations
import json
from .datamodels import *


class HumioParser:
    def build_alert_objects(self, raw_data, alert_field_name):
        return [self.build_alert_object(item, alert_field_name) for item in raw_data]

    @staticmethod
    def build_alert_object(raw_data, alert_field_name):
        raw_data.pop("@rawstring", None)

        return Alert(
            raw_data=raw_data,
            id=raw_data.get("@id"),
            timestamp=raw_data.get("@timestamp"),
            alert_field_name=alert_field_name,
        )

    def build_event_objects(self, raw_data):
        return [self.build_event_object(item) for item in raw_data]

    @staticmethod
    def build_event_object(raw_data):
        if raw_data.get("@rawstring"):
            raw_data["@rawstring"] = json.loads(raw_data.get("@rawstring"))

        return Event(raw_data=raw_data)
