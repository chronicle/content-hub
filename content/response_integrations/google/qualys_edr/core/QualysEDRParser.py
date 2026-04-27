from __future__ import annotations
from .datamodels import *


class QualysEDRParser:
    @staticmethod
    def build_alert_object(raw_data):
        return Alert(
            raw_data=raw_data,
            id=raw_data.get("id"),
            type=raw_data.get("type"),
            score=raw_data.get("score"),
            datetime=raw_data.get("dateTime"),
        )
