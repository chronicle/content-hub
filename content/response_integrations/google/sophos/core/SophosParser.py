from __future__ import annotations
from .datamodels import *


class SophosParser:
    def build_results(
        self, raw_json, method, data_key="data", pure_data=False, limit=None, **kwargs
    ):
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[
                :limit
            ]
        ]

    def build_alerts_list(self, raw_data):
        return [self.build_alert_object(item) for item in raw_data]

    def build_alert_object(self, raw_data):
        return Alert(
            raw_data=raw_data,
            id=raw_data.get("id"),
            threat=raw_data.get("threat"),
            description=raw_data.get("description"),
            severity=raw_data.get("severity"),
            alert_type=raw_data.get("type"),
            when=raw_data.get("when"),
        )

    def get_acces_token(self, raw_data):
        return raw_data.get("access_token")

    def build_api_root_details_obj(self, raw_data):
        return Api_Root(
            raw_data=raw_data,
            id=raw_data.get("id"),
            api_root=raw_data.get("apiHosts", {}).get("dataRegion"),
        )

    def build_endpoint_obj(self, raw_data):
        return Endpoint(
            raw_data=raw_data,
            hostname=raw_data.get("hostname", ""),
            ip_address=raw_data.get("ipv4Addresses", []),
            scan_id=raw_data.get("id", ""),
            service_info=raw_data.get("health", {}).get("services"),
            service_details=self.build_results(
                raw_data.get("health", {}).get("services", {}),
                method="build_service_details_obj",
                data_key="serviceDetails",
            ),
            health=raw_data.get("health", {}).get("overall"),
            threat_status=raw_data.get("health", {}).get("threats", {}).get("status"),
            services_status=raw_data.get("health", {})
            .get("services", {})
            .get("status"),
            type=raw_data.get("type"),
            os_name=raw_data.get("os", {}).get("name"),
            os_build=raw_data.get("os", {}).get("build"),
            mac_address=raw_data.get("macAddresses", []),
            associated_person=raw_data.get("associatedPerson", {}).get("name"),
            is_server=raw_data.get("os", {}).get("isServer"),
            last_seen_at=raw_data.get("lastSeenAt"),
        )

    def build_hash_obj(self, raw_data):
        return FileHash(
            raw_data=raw_data,
            type=raw_data.get("type"),
            comment=raw_data.get("comment"),
            created_at=raw_data.get("createdAt"),
            hash_value=raw_data.get("properties", {}).get(raw_data.get("type")),
        )

    def build_service_details_obj(self, raw_data):
        return ServiceDetails(
            raw_data=raw_data,
            status=raw_data.get("status", ""),
            name=raw_data.get("name", ""),
        )

    def build_event_obj(self, raw_data):
        return Events(
            raw_data=raw_data,
            name=raw_data.get("name", ""),
            type=raw_data.get("type", ""),
            source=raw_data.get("source", ""),
            threat=raw_data.get("threat", ""),
            severity=raw_data.get("severity", ""),
            timestamp=raw_data.get("when", ""),
        )

    def get_next_cursor(self, raw_data):
        return raw_data.get("next_cursor", "")

    def has_endpoint_more_events(self, raw_data):
        return raw_data.get("has_more")
