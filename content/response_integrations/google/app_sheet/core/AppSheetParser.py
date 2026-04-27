from __future__ import annotations
from .datamodels import Table, Record

class AppSheetParser:
    def build_search_records_object(self, raw_data):
        return [self.build_search_record_object(item) for item in raw_data]

    def build_search_record_object(self, raw_data):
        return Record(raw_data=raw_data)

    def build_table_list(self, raw_data):
        return [self.build_table_object(item) for item in raw_data]

    def build_table_object(self, raw_data):
        return Table(
            raw_data=raw_data, id=raw_data.get("id"), name=raw_data.get("name")
        )
