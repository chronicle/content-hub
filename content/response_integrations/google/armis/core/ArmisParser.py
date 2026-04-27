from __future__ import annotations
from .datamodels import (
    AlertResponse,
    AlertResponseData,
    Alert,
    Device,
    Activity,
    DeviceAlert,
    AlertConnectionResponse,
    AlertConnectionResponseData,
    AlertConnection,
)
from typing import List, Dict, Optional
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time


class ArmisParser:
    """
    Armis Parser
    """

    @staticmethod
    def build_alert_response_object(response) -> AlertResponse:
        raw_data = response.json()
        return AlertResponse(
            raw_data=raw_data,
            success=raw_data.get("success", False),
            data=ArmisParser.build_alert_response_data_object(raw_data.get("data", {})),
        )

    @staticmethod
    def build_alert_response_data_object(data) -> AlertResponseData:
        alerts = ArmisParser.build_alerts_object(data.get("results", []))
        return AlertResponseData(raw_data=data, alerts=alerts, **data)

    @staticmethod
    def build_alerts_object(results) -> List[Alert]:
        alerts = []
        for alert_dict in results:
            time_value = convert_string_to_unix_time(alert_dict.get("time"))
            alerts.append(
                Alert(raw_data=alert_dict, time_value=time_value, **alert_dict)
            )

        return alerts

    @staticmethod
    def build_device_objects(response) -> List[DeviceAlert]:
        return [
            ArmisParser.build_device_object(device)
            for device in response.json().get("data", {}).get("results", [])
        ]

    @staticmethod
    def build_device_object(raw_data) -> DeviceAlert:
        return DeviceAlert(raw_data=raw_data, **raw_data)

    @staticmethod
    def build_activity_objects(response) -> List[Activity]:
        return [
            ArmisParser.build_activity_object(activity)
            for activity in response.json().get("data", {}).get("results", [])
        ]

    @staticmethod
    def build_activity_object(raw_data) -> Activity:
        time_value = convert_string_to_unix_time(raw_data.get("time"))
        return Activity(raw_data=raw_data, time_value=time_value, **raw_data)

    @staticmethod
    def build_device_obj(raw_data: Dict, api_root: Optional[str] = None) -> Device:
        raw_device = raw_data.get("data", {}).get("data", [])
        if not raw_device:  # No device was matched
            return None
        raw_device = raw_device[0]
        return Device(
            raw_data=raw_device,
            risk_level=raw_device.get("riskLevel"),
            device_id=raw_device.get("id"),
            type=raw_device.get("type"),
            api_root=api_root,
            category=raw_device.get("category"),
            ip_address=raw_device.get("ipAddress"),
            mac_address=raw_device.get("macAddress"),
            name=raw_device.get("name"),
            os=raw_device.get("operatingSystem"),
            os_version=raw_device.get("operatingSystemVersion"),
            purdue_level=raw_device.get("purdueLevel"),
            tags=raw_device.get("tags"),
            user=raw_device.get("user"),
            visibility=raw_device.get("visibility"),
            site=raw_device.get("site"),
            site_name=raw_device.get("site", {}).get("name"),
        )

    @staticmethod
    def build_alert_connection_response_object(response) -> AlertConnectionResponse:
        raw_data = response.json()
        return AlertConnectionResponse(
            raw_data=raw_data,
            success=raw_data.get("success", False),
            data=ArmisParser.build_alert_connection_response_data_object(
                raw_data.get("data", {})
            ),
        )

    @staticmethod
    def build_alert_connection_response_data_object(
        data,
    ) -> AlertConnectionResponseData:
        alert_connections = ArmisParser.build_alerts_connections_object(
            data.get("results", [])
        )
        return AlertConnectionResponseData(
            raw_data=data, alert_connections=alert_connections, **data
        )

    @staticmethod
    def build_alerts_connections_object(results) -> List[AlertConnection]:
        alert_connections = []
        for alert_connection_dict in results:
            # time_value = convert_string_to_unix_time(alert_connection_dict.get('time'))
            alert_connections.append(
                AlertConnection(raw_data=alert_connection_dict, **alert_connection_dict)
            )

        return alert_connections
