from __future__ import annotations
from .datamodels import *


class ArcSightLoggerParser:
    def get_auth_token(self, raw_json):
        return raw_json.get("log.loginResponse", "").get("log.return")

    def build_query_status_object(self, result_json):
        return QueryStatus(
            result_json,
            status=result_json.get("status"),
            result_type=result_json.get("result_type"),
            hit=result_json.get("hit"),
            scanned=result_json.get("scanned"),
            elapsed=result_json.get("elapsed"),
            message=result_json.get("message"),
        )
