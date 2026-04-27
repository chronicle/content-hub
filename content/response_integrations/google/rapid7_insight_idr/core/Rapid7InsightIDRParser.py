from __future__ import annotations
from .datamodels import *


class Rapid7InsightIDRParser:
    def build_investigation_objects(self, raw_data, data_key="data", pure_data=False):
        return [
            self.build_investigation_object(item)
            for item in (raw_data if pure_data else raw_data.get(data_key, []))
        ]

    def build_investigation_object(self, raw_data: dict) -> Investigation:
        return Investigation(
            raw_data=raw_data,
            title=raw_data.get("title", ""),
            status=raw_data.get("status", ""),
            source=raw_data.get("source", ""),
            assignee_email=(
                raw_data.get("assignee", {}).get("email", "")
                if raw_data.get("assignee")
                else ""
            ),
            alert_types=[alert.get("type", "") for alert in raw_data.get("alerts", [])],
            created_time=raw_data.get("created_time", ""),
            rrn=raw_data.get("rrn", ""),
            priority=raw_data.get("priority", ""),
            first_alert_time=raw_data.get("first_alert_time", ""),
            latest_alert_time=raw_data.get("latest_alert_time", ""),
        )

    def build_saved_query_objects(self, raw_data):
        return [
            self.build_saved_query_object(saved_query)
            for saved_query in raw_data.get("saved_queries", [])
        ]

    def build_saved_query_object(self, raw_data):
        return SavedQuery(
            raw_data=raw_data,
            id=raw_data.get("id", ""),
            name=raw_data.get("name", ""),
            statement=raw_data.get("leql", {}).get("statement", ""),
            time_range=raw_data.get("leql", {}).get("during", {}).get("time_range", ""),
            start_time=raw_data.get("leql", {}).get("during", {}).get("to", ""),
            end_time=raw_data.get("leql", {}).get("during", {}).get("from", ""),
            logs=raw_data.get("logs", []),
        )

    def get_saved_query_object(self, raw_data):
        return self.build_saved_query_object(raw_data.get("saved_query", {}))

    def get_logs_ids(self, raw_data, log_names):
        return [
            log.get("id")
            for log in raw_data.get("logs", [])
            if log.get("name") in log_names
        ]

    def get_saved_query_results(self, raw_data):
        results = raw_data.get("events", [])
        link = raw_data.get("links")[0].get("href") if raw_data.get("links") else None
        return results, link
