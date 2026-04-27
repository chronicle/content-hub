from __future__ import annotations
from .datamodels import *


class AnomaliParser:
    def build_results(self, raw_json, method, pure_data=False, limit=None, *kwargs):
        return [
            getattr(self, method)(item_json, *kwargs)
            for item_json in (raw_json if pure_data else raw_json.get("objects", []))[
                :limit
            ]
        ]

    def build_result(self, raw_json, method, *kwargs):
        return getattr(self, method)(raw_json.get("objects", {}), *kwargs)

    @staticmethod
    def build_threat(raw_json):
        return Threat(
            raw_data=raw_json,
            threat_id=raw_json.get("id"),
            severity=raw_json.get("meta", {}).get("severity"),
            names=(
                [tag.get("name", "") for tag in raw_json.get("tags", [])]
                if raw_json.get("tags")
                else ""
            ),
            **raw_json
        )

    @staticmethod
    def get_next_cursor(raw_json):
        return raw_json.get("meta", {}).get("next")

    @staticmethod
    def build_indicator_object(raw_json):
        return Indicator(raw_json, **raw_json)

    @staticmethod
    def build_association_object(raw_json):
        return Associations(raw_json, **raw_json)

    @staticmethod
    def build_association_details_object(raw_json):
        if isinstance(raw_json.get("status", {}), dict):
            status_display_name = raw_json.get("status", {}).get("display_name", "")
        else:
            status_display_name = raw_json.get("status", "")

        return AssociationDetails(
            raw_data=raw_json, status_display_name=status_display_name, **raw_json
        )
