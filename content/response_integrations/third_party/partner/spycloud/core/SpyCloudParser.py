from __future__ import annotations
from .datamodels import *


class SpyCloudParser:
    def build_list_of_catalog_objects(self, raw_data):
        return [self.build_catalog_object(item) for item in raw_data]

    @staticmethod
    def build_catalog_object(raw_data):
        return Catalog(
            raw_data=raw_data,
            title=raw_data.get("title"),
            type=raw_data.get("type"),
            num_records=raw_data.get("num_records"),
            site=raw_data.get("site"),
            id=raw_data.get("id"),
        )

    def build_list_of_breach_objects(self, raw_data):
        return [self.build_breach_object(item) for item in raw_data.get("results", [])]

    @staticmethod
    def build_breach_object(raw_data):
        return Breach(
            raw_data=raw_data,
            target_url=raw_data.get("target_url"),
            email=raw_data.get("email"),
            infected_time=raw_data.get("infected_time"),
            sighting=raw_data.get("sighting"),
            severity=raw_data.get("severity"),
            password=raw_data.get("password"),
        )
