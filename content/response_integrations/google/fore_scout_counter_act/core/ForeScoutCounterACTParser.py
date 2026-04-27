from __future__ import annotations
from .datamodels import EndpointInfo


class ForeScoutCounterACTParser:
    """
    ForeScout CounterACT Parsing layer
    """

    @staticmethod
    def build_endpoint_info_obj(raw_data):
        return EndpointInfo(
            raw_data=raw_data,
            ip_address=raw_data.get("host", {}).get("ip"),
            mac_address=raw_data.get("host", {}).get("mac"),
            onsite=raw_data.get("host", {})
            .get("fields", {})
            .get("onsite", {})
            .get("value"),
            guest_corporate_state=raw_data.get("host", {})
            .get("fields", {})
            .get("guest_corporate_state", {})
            .get("value"),
            fingerprint=raw_data.get("host", {})
            .get("fields", {})
            .get("fingerprint", {})
            .get("value"),
            vendor=raw_data.get("host", {})
            .get("fields", {})
            .get("vendor", {})
            .get("value"),
            classification=raw_data.get("host", {})
            .get("fields", {})
            .get("prim_classification", {})
            .get("value"),
            agent_version=raw_data.get("host", {})
            .get("fields", {})
            .get("agent_version", {})
            .get("value"),
            online=raw_data.get("host", {})
            .get("fields", {})
            .get("online", {})
            .get("value"),
        )
