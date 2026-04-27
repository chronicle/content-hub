from __future__ import annotations
from typing import Union
from .datamodels import *


class McAfeeESMParser:
    def build_results(
        self,
        raw_json: Union[Dict, List],
        method: str,
        data_key: str = "results",
        limit: int = None,
        pure_data: bool = False,
        **kwargs: str,
    ) -> List:
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (raw_json if pure_data else raw_json.get(data_key, []))[
                :limit
            ]
        ]

    @staticmethod
    def build_alarm_object(raw_data: Dict) -> Alarm:
        return Alarm(
            raw_data=raw_data,
            alarm_id=raw_data.get("id"),
            name=raw_data.get("alarmName"),
            summary=raw_data.get("summary"),
            severity=raw_data.get("severity", -1),
            triggered_date=raw_data.get("triggeredDate"),
            source_events=raw_data.get("events", []),
        )

    @staticmethod
    def export_events_data_from_alarms_data(raw_data: Dict) -> List:
        return raw_data.get("events", [])

    @staticmethod
    def extract_correlated_ids(raw_data: Dict) -> List:
        return [
            item.get("eventId") for item in raw_data.get("list", []) if item.get("corr")
        ]

    @staticmethod
    def extract_event_ids(raw_data: Dict, extract_key: str = "values") -> List:
        event_ids = []
        results = raw_data.get("return", [])
        if results:
            for item in results:
                event_ids.extend(item.get(extract_key))
        return event_ids

    @staticmethod
    def build_correlation_alert_object(raw_data: Dict) -> CorrelationAlert:
        return CorrelationAlert(
            raw_data=raw_data,
            event_id=f'{raw_data.get("ipsId")}|{raw_data.get("alertId")}',
            sig_id=raw_data.get("sigId"),
            rule_name=raw_data.get("ruleName"),
            message=raw_data.get("normMessage"),
            description=raw_data.get("normDesc"),
            severity=raw_data.get("severity", -1),
            first_time=raw_data.get("firstTime"),
            last_time=raw_data.get("lastTime"),
        )

    @staticmethod
    def build_source_event_object(
        raw_data: Dict,
        time_format: str = None,
        time_zone: int = None,
        logger: object = None,
    ) -> SourceEvent:
        return SourceEvent(
            raw_data=raw_data,
            event_id=raw_data.get("ipsId"),
            first_time=raw_data.get("firstTime"),
            last_time=raw_data.get("lastTime"),
            time_zone=time_zone,
            time_format=time_format,
            logger=logger,
            rule_name=raw_data.get("ruleName"),
        )

    @staticmethod
    def build_query_result_object(raw_data: Dict) -> QueryResult:
        return QueryResult(
            raw_data=raw_data,
            complete=raw_data.get("complete", False),
            columns=raw_data.get("columns", []),
            rows=raw_data.get("rows", []),
        )

    @staticmethod
    def build_events_query_result_object(raw_data: Dict) -> EventsQueryResult:
        return EventsQueryResult(
            raw_data=raw_data,
            fields=raw_data.get("fields", []),
            data=raw_data.get("data", []),
        )

    @staticmethod
    def build_query_event_object(raw_data: Dict) -> QueryEvent:
        return QueryEvent(
            raw_data=raw_data,
            ips_id_alert_id=raw_data.get("Alert.IPSIDAlertID"),
            last_time=raw_data.get("Alert.LastTime"),
        )

    @staticmethod
    def build_watchlist_object(raw_data: Dict) -> Watchlist:
        return Watchlist(
            raw_data=raw_data,
            name=raw_data.get("name"),
            watchlist_id=raw_data.get("id"),
        )

    @staticmethod
    def build_advanced_query_result_object(raw_data: Dict) -> AdvancedQueryResult:
        return AdvancedQueryResult(raw_data=raw_data)
