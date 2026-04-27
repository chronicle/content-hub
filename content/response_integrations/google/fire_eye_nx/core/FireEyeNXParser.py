from __future__ import annotations
from .datamodels import *


class FireEyeNXParser:
    def build_alerts_array(self, raw_data):
        alerts_data = raw_data.get("alert", [])
        return [
            self.build_siemplify_alert_obj(alert_data=alert_data)
            for alert_data in alerts_data
        ]

    def build_siemplify_alert_obj(self, alert_data):
        return Alert(
            raw_data=alert_data,
            malwares=alert_data.get("explanation", {})
            .get("malwareDetected", {})
            .get("malware", []),
            cnc_services=alert_data.get("explanation", {})
            .get("cncServices", {})
            .get("cncService", []),
            src=alert_data.get("src", {}),
            url=alert_data.get("alertUrl"),
            action=alert_data.get("action"),
            occurred=alert_data.get("occurred"),
            attack_time=alert_data.get("attackTime"),
            dst=alert_data.get("dst", {}),
            appliance_id=alert_data.get("applianceId"),
            id=alert_data.get("id"),
            name=alert_data.get("name"),
            severity=alert_data.get("severity"),
            uuid=alert_data.get("uuid"),
            ack=alert_data.get("ack"),
            product=alert_data.get("product"),
            vlan=alert_data.get("vlan"),
            malicious=alert_data.get("malicious"),
            sc_version=alert_data.get("scVersion"),
        )
