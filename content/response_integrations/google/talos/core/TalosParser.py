from __future__ import annotations
from .datamodels import *


class TalosParser:
    def build_base_object(self, raw_data):
        return BaseModel(raw_data=raw_data)

    def build_whois_report_object(self, raw_data):
        return WhoisReport(raw_data=raw_data)

    def build_reputation_object(self, raw_data, reputation_type):
        return Reputation(raw_data=raw_data, reputation_type=reputation_type)
