from __future__ import annotations
from .datamodels import *


class HarmonyMobileParser:

    @staticmethod
    def get_token(raw_data):
        return raw_data.get("data", {}).get("token")

    @staticmethod
    def build_alert_object(raw_data):
        return Alert(
            raw_data=raw_data,
            id=raw_data.get("id"),
            details=raw_data.get("details"),
            severity=raw_data.get("severity"),
            threat_factors=raw_data.get("threat_factors"),
            timestamp=raw_data.get("backend_last_updated"),
        )

    @staticmethod
    def build_device_object(raw_data):
        return Device(
            raw_data=raw_data,
            client_version=raw_data.get("client_version"),
            device_type=raw_data.get("device_type"),
            email=raw_data.get("email"),
            last_connection=raw_data.get("last_connection"),
            model=raw_data.get("model"),
            name=raw_data.get("name"),
            number=raw_data.get("number"),
            os_type=raw_data.get("os_type"),
            os_version=raw_data.get("os_version"),
            risk=raw_data.get("risk"),
            status=raw_data.get("status"),
        )
