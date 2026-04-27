from __future__ import annotations
from .datamodels import *


class MandiantASMParser:
    def build_issue_object(self, raw_data):
        return Issue(raw_data, name=raw_data["name"])

    def build_asm_entity_object(self, raw_data):
        return ASMEntity(raw_data, name=raw_data["name"])

    def build_issue_objects(self, raw_data):
        return [self.build_issue_object(issue_dict) for issue_dict in raw_data]

    def build_asm_entity_objects(self, raw_data):
        return [self.build_asm_entity_object(entity_dict) for entity_dict in raw_data]

    def build_connector_issue_object(self, raw_data):
        return ConnectorIssue(
            raw_data=raw_data,
            issue_id=raw_data.get("id") or raw_data.get("uid"),
            pretty_name=raw_data.get("pretty_name"),
            proof=raw_data.get("details", {}).get("proof"),
            description=raw_data.get("description"),
            severity=raw_data.get("severity"),
            category=raw_data.get("category")
            or raw_data.get("summary", {}).get("category"),
            first_seen=raw_data.get("first_seen"),
            last_seen=raw_data.get("last_seen"),
        )
