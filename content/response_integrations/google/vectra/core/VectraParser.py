from __future__ import annotations
from .datamodels import *


class VectraParser:
    def build_endpoint_object(self, endpoint_json):
        return Endpoint(
            raw_data=endpoint_json,
            endpoint_id=endpoint_json.get("id"),
            name=endpoint_json.get("name"),
            state=endpoint_json.get("state"),
            threat=endpoint_json.get("threat"),
            certainty=endpoint_json.get("certainty"),
            ip=endpoint_json.get("last_source"),
            tags=endpoint_json.get("tags", []),
            note=endpoint_json.get("note"),
            url=endpoint_json.get("url"),
            last_modified=endpoint_json.get("last_modified"),
            groups=endpoint_json.get("groups", []),
            is_key_asset=endpoint_json.get("is_key_asset"),
            has_active_traffic=endpoint_json.get("has_active_traffic"),
            is_targeting_key_asset=endpoint_json.get("is_targeting_key_asset"),
            privilege_level=endpoint_json.get("privilege_level"),
            previous_ip=endpoint_json.get("previous_ips", []),
        )

    def build_detection_object(self, detection_json):
        return Detection(
            raw_data=detection_json,
            detection_id=detection_json.get("id"),
            name=detection_json.get("detection"),
            tags=detection_json.get("tags"),
            sensor_name=detection_json.get("sensor_name"),
            priority=detection_json.get("threat"),
            category=detection_json.get("category"),
            first_timestamp=detection_json.get("first_timestamp"),
            last_timestamp=detection_json.get("last_timestamp"),
            grouped_details=detection_json.get("grouped_details"),
            detection_category=detection_json.get("detection_category"),
            detection_type=detection_json.get("detection_type"),
            certainty=detection_json.get("certainty"),
            threat=detection_json.get("threat"),
        )

    def build_triage_rule_object(self, triage_rule_json):
        return TriageRule(
            raw_data=triage_rule_json,
            triage_id=triage_rule_json.get("id"),
            enabled=triage_rule_json.get("enabled"),
            detection_category=triage_rule_json.get("detection_category"),
            triage_category=triage_rule_json.get("triage_category"),
            detection=triage_rule_json.get("detection"),
            whitelist=triage_rule_json.get("is_whitelist"),
            priority=triage_rule_json.get("priority"),
            created_at=triage_rule_json.get("created_timestamp"),
            description=triage_rule_json.get("description"),
        )
