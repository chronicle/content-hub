from __future__ import annotations
from .datamodels import *


class CiscoISEParser:
    def build_endpoint_groups_list(self, raw_data):
        return [
            self.build_endpoint_group_object(item)
            for item in raw_data.get("SearchResult", {}).get("resources", [])
        ]

    def build_endpoint_group_object(self, raw_data):
        return EndpointGroup(
            raw_data=raw_data,
            id=raw_data.get("id"),
            name=raw_data.get("name"),
            description=raw_data.get("description"),
        )
