from __future__ import annotations
from open_search.core.data_models import DslSearchResult


class OpenSearchParser:
    def build_dsl_result_objects(self, raw_data):
        return [
            self._build_dsl_result_object(dsl_result_dict)
            for dsl_result_dict in raw_data
        ]

    def _build_dsl_result_object(self, dsl_result_dict):
        return DslSearchResult(
            raw_data=dsl_result_dict, alert_id=dsl_result_dict["_id"]
        )
