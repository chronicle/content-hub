from __future__ import annotations
from .datamodels import *


class NozomiNetworksParser:
    def build_all_objects(self, raw_json):
        return [
            self.build_vulnerability_object(object_json)
            for object_json in raw_json.get("result", [])
        ]

    def build_vulnerability_object(self, raw_json):
        return Vulnerability(
            raw_data=raw_json,
            node_id=raw_json.get("node_id"),
            cve=raw_json.get("cve"),
            cwe_name=raw_json.get("cwe_name"),
            cve_summary=raw_json.get("cve_summary"),
            cve_score=raw_json.get("cve_score"),
            zone=raw_json.get("zone"),
            resolved=raw_json.get("resolved"),
            cve_references=raw_json.get("cve_references"),
            cve_creation_time=raw_json.get("cve_creation_time"),
            cve_update_time=raw_json.get("cve_update_time"),
        )

    def build_query_results(self, raw_json):
        return [
            QueryResult(raw_data=query_json)
            for query_json in raw_json.get("result", [])
        ]

    def build_all_alerts(self, raw_json):
        return [
            self.build_alert_object(alert_json=alert_data)
            for alert_data in raw_json.get("result", [])
        ]

    def build_alert_object(self, alert_json):
        return Alert(
            raw_data=alert_json,
            id=alert_json.get("id"),
            description=alert_json.get("description"),
            type_name=alert_json.get("type_name"),
            name=alert_json.get("name"),
            severity=alert_json.get("severity"),
            created_time=alert_json.get("created_time"),
        )

    def build_node_objects(self, raw_json):
        return [
            Node(
                raw_data=node_json,
                level=node_json.get("level"),
                appliance_host=node_json.get("appliance_host"),
                ip=node_json.get("ip"),
                mac_address=node_json.get("mac_address"),
                vlan_id=node_json.get("vlan_id"),
                os=node_json.get("os"),
                roles=node_json.get("roles"),
                vendor=node_json.get("vendor"),
                firmware_version=node_json.get("firmware_version"),
                serial_number=node_json.get("serial_number"),
                product_name=node_json.get("product_name"),
                type=node_json.get("type"),
                protocols=node_json.get("protocols"),
                device_id=node_json.get("device_id"),
                capture_device=node_json.get("capture_device"),
                is_broadcast=node_json.get("is_broadcast"),
                is_public=node_json.get("is_public"),
                is_confirmed=node_json.get("is_confirmed"),
                is_disabled=node_json.get("is_disabled"),
                is_licensed=node_json.get("_is_licensed"),
                last_activity_time=node_json.get("last_activity_time"),
            )
            for node_json in raw_json.get("result", [])
        ]
