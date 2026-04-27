from __future__ import annotations
from .datamodels import *


class SolarWindsOrionParser:
    def build_all_query_results(self, raw_data):
        return [
            self.build_query_result_object(result_json=result_json)
            for result_json in raw_data.get("results", [])
        ]

    def build_query_result_object(self, result_json):
        return QueryResult(
            raw_data=result_json,
            ip_address=result_json.get("IpAddress"),
            display_name=result_json.get("DisplayName"),
        )

    def build_error_object(self, raw_data):
        return ErrorObject(raw_data=raw_data, message=raw_data.get("Message"))
