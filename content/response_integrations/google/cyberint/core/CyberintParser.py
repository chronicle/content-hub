from __future__ import annotations
from .datamodels import *


class CyberintParser:
    def build_alerts_list(self, raw_data):
        return [self.build_alert_object(item) for item in raw_data.get("alerts", [])]

    def build_alert_object(self, raw_data):
        return Alert(
            raw_data=raw_data,
            id=raw_data.get("ref_id"),
            title=raw_data.get("title"),
            description=raw_data.get("description"),
            severity=raw_data.get("severity"),
            type=raw_data.get("type"),
            created_date=raw_data.get("created_date"),
        )
