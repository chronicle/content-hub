from __future__ import annotations
from .datamodels import *


class SumoLogicCloudSIEMParser:
    def build_insights_list(self, raw_data):
        return [
            self.build_insight(item)
            for item in raw_data.get("data", {}).get("objects", [])
        ]

    def build_insight(self, raw_data):
        return Insight(
            raw_data=raw_data,
            id=raw_data.get("id"),
            readable_id=raw_data.get("readableId"),
            name=raw_data.get("name"),
            description=raw_data.get("description"),
            severity=raw_data.get("severity"),
            created=raw_data.get("created"),
        )

    def build_entity_info_objects(self, raw_data):
        return [
            self.build_entity_info_object(item)
            for item in raw_data.get("data", {}).get("objects", [])
        ]

    @staticmethod
    def build_entity_info_object(raw_data):
        return EntityInfo(
            raw_data=raw_data,
            name=raw_data.get("name"),
            is_suppressed=raw_data.get("isSuppressed"),
            is_whitelisted=raw_data.get("isWhitelisted"),
            tags=raw_data.get("tags"),
            first_seen=raw_data.get("firstSeen"),
            last_seen=raw_data.get("lastSeen"),
            criticality=raw_data.get("criticality"),
            activity_score=raw_data.get("activityScore"),
        )

    def build_signal_objects(self, raw_data):
        return [
            self.build_signal_object(item)
            for item in raw_data.get("data", {}).get("objects", [])
        ]

    @staticmethod
    def build_signal_object(raw_data):
        return Signal(raw_data=raw_data)
