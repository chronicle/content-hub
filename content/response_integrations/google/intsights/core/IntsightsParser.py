from __future__ import annotations
from .datamodels import *


class IntsightsParser:
    def build_iocs_object(self, raw_data):
        return Iocs(raw_data=raw_data, **raw_data)

    def build_alert_obj(self, raw_data):
        return Alert(
            raw_data=raw_data,
            network_type=raw_data.get("Details", {})
            .get("Source", {})
            .get("NetworkType"),
            alert_type=raw_data.get("Details", {}).get("Source", {}).get("Type"),
            severity=raw_data.get("Details", {}).get("Severity", {}),
            title=raw_data.get("Details", {}).get("Title"),
            **raw_data
        )
