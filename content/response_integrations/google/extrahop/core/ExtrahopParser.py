from __future__ import annotations
from extrahop.core.datamodels import *


class ExtrahopParser:
    def build_detections_list(self, raw_data):
        return [self.build_detection(item) for item in raw_data]

    def build_detection(self, raw_data):
        return Detection(
            raw_data=raw_data,
            id=f'{raw_data.get("id")}',
            title=raw_data.get("title"),
            description=raw_data.get("description"),
            risk_score=raw_data.get("risk_score"),
            type=raw_data.get("type"),
            update_time=raw_data.get("update_time"),
            participants=raw_data.get("participants", []),
        )

    def build_device(self, raw_data):
        return Device(raw_data=raw_data, id=raw_data.get("id"))
