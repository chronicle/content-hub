from __future__ import annotations
from .datamodels import *


class InternetStormCenterParser:
    def build_device_obj(self, raw_json):
        raw_data = raw_json.get("ip", {})
        if raw_data:
            return Device(
                raw_data=raw_data,
                count=raw_data.get("count"),
                attacks=raw_data.get("attacks"),
                first_seen=raw_data.get("mindate"),
                last_seen=raw_data.get("maxdate"),
                comment=raw_data.get("comment"),
                max_risk=raw_data.get("maxrisk"),
                asabuse_contact=raw_data.get("asabusecontact"),
                as_name=raw_data.get("asname"),
                as_country=raw_data.get("ascountry"),
                threat_feeds=", ".join(
                    [k for k, v in raw_data.get("threatfeeds", {}).items()]
                ),
            )
