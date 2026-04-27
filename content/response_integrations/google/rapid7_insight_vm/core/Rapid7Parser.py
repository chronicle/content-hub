from __future__ import annotations
from .datamodels import *


class Rapid7Parser:
    def build_asset_object(self, raw_data):
        return Asset(raw_data=raw_data, id=raw_data.get("id"), ip=raw_data.get("ip"))

    def build_vulnerability_object(self, raw_data):
        return Vulnerability(
            raw_data=raw_data, id=raw_data.get("id"), since=raw_data.get("since")
        )

    def build_vulnerability_details_object(self, raw_data):
        return VulnerabilityDetails(
            raw_data=raw_data,
            id=raw_data.get("id"),
            title=raw_data.get("title"),
            severity=raw_data.get("severity"),
        )
