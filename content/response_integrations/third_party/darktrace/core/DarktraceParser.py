from __future__ import annotations

from datamodels import (
    AiAlert,
    Alert,
    ConnectionData,
    Device,
    EndpointDetails,
    Event,
    ModelBreach,
    SearchResult,
)


class DarktraceParser:
    def build_ai_alert_objects(self, raw_data: dict) -> list[AiAlert]:
        return [self.build_ai_alert_object(item) for item in raw_data]

    @staticmethod
    def build_ai_alert_object(raw_data: dict) -> AiAlert:
        return AiAlert(
            raw_data=raw_data,
            alert_id=raw_data.get("id"),
            name=raw_data.get("title"),
            description=raw_data.get("summary"),
            score=raw_data.get("aiaScore"),
            time=raw_data.get("createdAt"),
            source_grouping_identifier=raw_data.get("currentGroup"),
            start_time=raw_data.get("periods", [{}])[0].get("start"),
            end_time=raw_data.get("periods", [{}])[0].get("end"),
        )

    def build_alert_objects(self, raw_data):
        return [self.build_alert_object(item) for item in raw_data]

    @staticmethod
    def build_alert_object(raw_data):
        return Alert(
            raw_data=raw_data,
            id=raw_data.get("pbid"),
            name=(
                raw_data.get("model", {}).get("now", {}).get("name")
                if raw_data.get("model", {}).get("now", {})
                else raw_data.get("model", {}).get("then", {}).get("name")
            ),
            description=(
                raw_data.get("model", {}).get("now", {}).get("description")
                if raw_data.get("model", {}).get("now", {})
                else raw_data.get("model", {}).get("then", {}).get("description")
            ),
            score=raw_data.get("score"),
            time=raw_data.get("time"),
        )

    def build_device_objects_list(self, raw_data):
        return [self.build_device_object(item) for item in raw_data]

    def build_device_object(self, raw_data):
        device_raw_data = (
            self.get_device_from_list(raw_data) if isinstance(raw_data, list) else raw_data
        )

        if device_raw_data:
            return Device(
                raw_data=device_raw_data,
                mac_address=device_raw_data.get("macaddress"),
                id=device_raw_data.get("id"),
                ip=device_raw_data.get("ip"),
                did=device_raw_data.get("did"),
                os=device_raw_data.get("os"),
                hostname=device_raw_data.get("hostname"),
                type_label=device_raw_data.get("typelabel"),
                device_label=device_raw_data.get("devicelabel"),
                typename=device_raw_data.get("typename"),
                first_seen=device_raw_data.get("firstSeen"),
                last_seen=device_raw_data.get("lastSeen"),
            )

    @staticmethod
    def build_endpoint_details_object(raw_data):
        return EndpointDetails(
            raw_data=raw_data,
            ip=raw_data.get("ip"),
            country=raw_data.get("country"),
            asn=raw_data.get("asn"),
            city=raw_data.get("city"),
            region=raw_data.get("region"),
            hostname=raw_data.get("hostname"),
            name=raw_data.get("name"),
            longitude=raw_data.get("longitude"),
            latitude=raw_data.get("latitude"),
            devices=raw_data.get("devices", []),
            ips=raw_data.get("ips", []),
            locations=raw_data.get("locations", []),
        )

    def get_device_object(self, raw_data):
        sorted_devices = sorted(
            raw_data.get("devices", []),
            key=lambda device: device["lastSeen"],
            reverse=True,
        )
        return self.build_device_object(sorted_devices[0]) if sorted_devices else None

    @staticmethod
    def get_device_from_list(raw_data):
        sorted_data = sorted(raw_data, key=lambda device: device["endtime"], reverse=True)
        return sorted_data[0] if sorted_data else None

    @staticmethod
    def build_model_breach_object(raw_data):
        return ModelBreach(
            raw_data=raw_data,
            acknowledged=True if raw_data.get("acknowledged") else False,
        )

    @staticmethod
    def build_event_objects(raw_data):
        return [Event(raw_data=item) for item in raw_data]

    @staticmethod
    def build_connection_data_object(raw_data):
        return ConnectionData(raw_data=raw_data)

    def build_search_result_objects(self, raw_data):
        return [
            self.build_search_result_object(item)
            for item in raw_data.get("hits", {}).get("hits", [])
        ]

    @staticmethod
    def build_search_result_object(raw_data):
        return SearchResult(raw_data=raw_data)
