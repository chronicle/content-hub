from __future__ import annotations
from .datamodels import *


class GoogleAlertCenterParser:
    def build_alert_objects(self, raw_data):
        return [self.build_alert_object(item) for item in raw_data.get("alerts", [])]

    @staticmethod
    def build_alert_object(raw_data):
        return Alert(
            raw_data=raw_data,
            alert_id=raw_data.get("alertId"),
            type=raw_data.get("type"),
            source=raw_data.get("source"),
            severity=raw_data.get("metadata", {}).get("severity"),
            start_time=raw_data.get("startTime"),
            end_time=raw_data.get("endTime"),
            create_time=raw_data.get("createTime"),
            messages=raw_data.get("data", {}).get("messages", []),
        )
