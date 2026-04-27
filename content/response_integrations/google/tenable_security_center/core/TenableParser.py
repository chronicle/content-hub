from __future__ import annotations
from .datamodels import *


class TenableParser:
    def get_asset_id(self, raw_data, asset_name):
        assets = raw_data.get("response", {}).get("usable", [])
        return next(
            (
                asset.get("id", "")
                for asset in assets
                if asset.get("name", "") == asset_name
            ),
            "",
        )

    def build_scan_object(self, raw_data):
        response = raw_data.get("response")

        return Scan(raw_data=response)

    def build_ip_list_asset(self, raw_data):
        raw_json = raw_data.get("response")

        return IPListAsset(
            raw_data=raw_json,
            defined_ips=raw_json.get("typeFields", {}).get("definedIPs"),
        )

    def build_ip_object(self, raw_data):
        response = raw_data.get("response", {})

        return EnrichIP(raw_data=response)
