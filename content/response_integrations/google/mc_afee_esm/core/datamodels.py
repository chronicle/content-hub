from __future__ import annotations
import copy
from _datetime import datetime, timedelta
from typing import Dict, List

from TIPCommon import dict_to_flat, add_prefix_to_dict
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from soar_sdk.SiemplifyLogger import SiemplifyLogger
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from EnvironmentCommon import EnvironmentHandle
from .constants import DEVICE_VENDOR, DEVICE_PRODUCT


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data: Dict) -> None:
        self.raw_data = raw_data

    def to_json(self) -> Dict:
        return self.raw_data

    def to_table(self) -> Dict:
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix: str = None) -> Dict:
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Alarm(BaseModel):
    def __init__(
        self,
        raw_data: Dict,
        alarm_id: str,
        name: str,
        summary: str,
        severity: int,
        triggered_date: str,
        source_events: List,
    ) -> None:
        super(Alarm, self).__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.alarm_id = alarm_id
        self.name = name
        self.summary = summary
        self.severity = severity
        self.triggered_date = triggered_date
        self.alarm_date_ms = convert_string_to_unix_time(self.triggered_date + "Z")
        self.source_events = source_events
        self.correlation_events = []
        self.utc_triggered_date = None

    def get_alert_info(
        self,
        alert_info: AlertInfo,
        environment_common: EnvironmentHandle,
        device_product_field: str,
        secondary_device_product_field: str,
        rule_generator_field_name: str,
        time_format: str = None,
        time_zone: int = None,
        logger: SiemplifyLogger = None,
    ) -> AlertInfo:
        alert_info.ticket_id = self.alarm_id
        alert_info.display_id = self.alarm_id
        alert_info.name = self.name
        alert_info.description = self.summary
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.priority = self.get_siemplify_severity()
        alert_info.source_grouping_identifier = self.name

        if time_format and time_zone:
            try:
                dt = datetime.strptime(self.triggered_date, time_format)
                self.utc_triggered_date = (dt + timedelta(hours=time_zone)).strftime(
                    time_format
                )
            except ValueError:
                logger.info(
                    f"Incorrect Time Format provided for 'triggeredDate'. "
                    f"Connector will ignore the provided value."
                )

        if self.utc_triggered_date:
            alert_info.start_time = convert_string_to_unix_time(
                self.utc_triggered_date + "Z"
            )
            alert_info.end_time = convert_string_to_unix_time(
                self.utc_triggered_date + "Z"
            )
        else:
            alert_info.start_time = self.alarm_date_ms
            alert_info.end_time = self.alarm_date_ms
        alert_info.events = self.to_events()
        alert_info.environment = environment_common.get_environment(
            alert_info.events[0]
        )
        alert_info.device_product = (
            alert_info.events[0].get(device_product_field)
            or alert_info.events[0].get(secondary_device_product_field)
            or DEVICE_PRODUCT
        )
        rule_gen_str = alert_info.events[0].get(rule_generator_field_name, self.name)
        alert_info.rule_generator = f"{DEVICE_PRODUCT}: {rule_gen_str}"

        return alert_info

    def get_siemplify_severity(self) -> int:
        # Informative.
        if int(self.severity) < 40:
            return -1
        # Low
        elif 39 < int(self.severity) < 60:
            return 40
        # Medium
        elif 59 < int(self.severity) < 80:
            return 60
        # High
        elif 79 < int(self.severity) < 100:
            return 80
        # Critical
        return 100

    def to_events(self) -> List:
        event_data = copy.deepcopy(self.raw_data)
        event_data["data_type"] = "Alarm"
        if self.utc_triggered_date:
            event_data["utc_triggeredDate"] = self.utc_triggered_date
        event_data.pop("events", None)
        events = []
        for source_event in self.source_events:
            events.append(
                source_event.to_event(
                    alarm_id=self.alarm_id, triggered_date=self.triggered_date
                )
            )
        for corr_event in self.correlation_events:
            events.append(
                corr_event.to_event(
                    alarm_id=self.alarm_id,
                    triggered_date=self.triggered_date,
                    is_corr=True,
                )
            )
        events.append(dict_to_flat(event_data))
        return events


class SourceEvent(BaseModel):
    def __init__(
        self,
        raw_data: Dict,
        event_id: str = None,
        first_time: str = None,
        last_time: str = None,
        time_format: str = None,
        time_zone: int = None,
        logger: SiemplifyLogger = None,
        rule_name: str = None,
    ) -> None:
        super(SourceEvent, self).__init__(raw_data)
        self.event_id = event_id
        self.utc_first_time = None
        self.utc_last_time = None
        self.rule_name = rule_name
        if logger:
            self.logger = logger

        if time_format and time_zone:
            try:
                dt_first = datetime.strptime(first_time, time_format)
                dt_last = datetime.strptime(last_time, time_format)
                self.utc_first_time = (dt_first + timedelta(hours=time_zone)).strftime(
                    time_format
                )
                self.utc_last_time = (dt_last + timedelta(hours=time_zone)).strftime(
                    time_format
                )
            except ValueError:
                logger.info(
                    f"Incorrect Time Format provided for 'firstTime'/'lastTime'. "
                    f"Connector will ignore the provided value."
                )

    def to_event(
        self, alarm_id: str = None, triggered_date: str = None, is_corr: bool = False
    ) -> Dict:
        main_data = copy.deepcopy(self.raw_data)
        main_data["data_type"] = "Correlation Event" if is_corr else "Source Event"
        main_data["alarm_id"] = alarm_id
        main_data["alarmId"] = alarm_id
        main_data["alarm_triggered_time"] = triggered_date
        if alarm_id:
            main_data["alarm_id"] = alarm_id
        if triggered_date:
            main_data["alarm_triggered_time"] = triggered_date
        custom_types = main_data.pop("customTypes", [])
        custom_type_fields = {}
        empty = object()

        for custom_type in custom_types:
            field_key = custom_type.get("fieldName", empty)
            field_value = custom_type.get("formatedValue", empty)

            if field_key is not empty and main_data.get(field_key, empty) is empty:
                main_data[field_key] = field_value

            elif field_key is not empty:
                if hasattr(self, "logger"):
                    self.logger.warn(
                        f"Custom field {field_key} with value {field_value} is present in event fields with value {main_data.get(field_key)}. "
                        f"Ignoring custom field value... "
                    )

            custom_type_fields[custom_type.get("fieldName", "")] = custom_type.get(
                "formatedValue", ""
            )
        main_data["customTypeFields"] = custom_type_fields

        if self.utc_first_time:
            main_data["utc_firstTime"] = self.utc_first_time
        if self.utc_last_time:
            main_data["utc_lastTime"] = self.utc_last_time

        return dict_to_flat(main_data)


class CorrelationAlert(SourceEvent):
    def __init__(
        self,
        raw_data: Dict,
        event_id: str,
        sig_id: str,
        rule_name: str,
        message: str,
        description: str,
        severity: int,
        first_time: str,
        last_time: str,
    ) -> None:
        super(CorrelationAlert, self).__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.event_id = event_id
        self.sig_id = sig_id
        self.rule_name = rule_name
        self.message = message
        self.description = description
        self.severity = severity
        self.first_time = first_time
        self.last_time = last_time
        self.first_time_ms = convert_string_to_unix_time(self.first_time + "Z")
        self.last_time_ms = convert_string_to_unix_time(self.last_time + "Z")
        self.source_events = []
        self.utc_first_time = None
        self.utc_last_time = None

    def get_alert_info(
        self,
        alert_info: AlertInfo,
        environment_common: EnvironmentHandle,
        device_product_field: str,
        secondary_device_product_field: str,
        rule_generator_field_name: str,
        time_format: str = None,
        time_zone: int = None,
        logger: SiemplifyLogger = None,
    ) -> AlertInfo:
        alert_info.ticket_id = self.event_id
        alert_info.display_id = self.event_id
        alert_info.name = self.rule_name
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.priority = self.get_siemplify_severity()
        alert_info.source_grouping_identifier = self.rule_name

        if time_format and time_zone:
            try:
                dt_first = datetime.strptime(self.first_time, time_format)
                dt_last = datetime.strptime(self.last_time, time_format)
                self.utc_first_time = (dt_first + timedelta(hours=time_zone)).strftime(
                    time_format
                )
                self.utc_last_time = (dt_last + timedelta(hours=time_zone)).strftime(
                    time_format
                )
            except ValueError:
                logger.info(
                    f"Incorrect Time Format provided for 'firstTime'/'lastTime'. "
                    f"Connector will ignore the provided value."
                )

        if self.utc_first_time:
            alert_info.start_time = convert_string_to_unix_time(
                self.utc_first_time + "Z"
            )
        else:
            alert_info.start_time = self.first_time_ms

        if self.utc_last_time:
            alert_info.end_time = convert_string_to_unix_time(self.utc_last_time + "Z")
        else:
            alert_info.end_time = self.last_time_ms

        alert_info.events = self.to_events()
        alert_info.environment = environment_common.get_environment(
            alert_info.events[0]
        )
        alert_info.device_product = (
            alert_info.events[0].get(device_product_field)
            or alert_info.events[0].get(secondary_device_product_field)
            or DEVICE_PRODUCT
        )
        rule_gen_str = alert_info.events[0].get(
            rule_generator_field_name, self.rule_name
        )
        alert_info.rule_generator = f"{DEVICE_PRODUCT}:{rule_gen_str}"
        alert_info.extensions = self.to_event()

        return alert_info

    def get_siemplify_severity(self) -> int:
        # Informative.
        if int(self.severity) < 40:
            return -1
        # Low
        elif 39 < int(self.severity) < 60:
            return 40
        # Medium
        elif 59 < int(self.severity) < 80:
            return 60
        # High
        elif 79 < int(self.severity) < 100:
            return 80
        # Critical
        return 100

    def to_events(self) -> List:
        main_data = self.to_event()
        main_data["data_type"] = "Correlation"
        main_data["McAfee_eventId"] = self.rule_name
        main_data["StartTime"] = self.first_time_ms
        main_data["EndTime"] = self.last_time_ms

        events = [dict_to_flat(main_data)]
        for source_event in self.source_events:
            event_data = source_event.to_event()
            event_data["McAfee_eventId"] = source_event.rule_name
            event_data["StartTime"] = convert_string_to_unix_time(
                event_data["firstTime"] + "Z"
            )
            event_data["EndTime"] = convert_string_to_unix_time(
                event_data["lastTime"] + "Z"
            )
            events.append(event_data)

        return events


class QueryResult(BaseModel):
    def __init__(
        self, raw_data: Dict, complete: bool, columns: List, rows: List
    ) -> None:
        super(QueryResult, self).__init__(raw_data)
        self.complete = complete
        self.columns = columns
        self.rows = rows

    def to_json_list(self) -> List:
        return [
            {
                column["name"].replace(".", "_"): column_value
                for column, column_value in zip(self.columns, row["values"])
            }
            for row in self.rows
        ]


class EventsQueryResult(BaseModel):
    def __init__(self, raw_data: Dict, fields: List, data: List) -> None:
        super(EventsQueryResult, self).__init__(raw_data)
        self.fields = fields
        self.data = data

    def to_json_list(self) -> List:
        return [
            {
                field["field"]: field_value
                for field, field_value in zip(self.fields, row)
            }
            for row in self.data
        ]


class QueryEvent(BaseModel):
    def __init__(self, raw_data: Dict, ips_id_alert_id: str, last_time: str) -> None:
        super(QueryEvent, self).__init__(raw_data)
        self.ips_id_alert_id = ips_id_alert_id
        self.last_time = last_time
        self.last_time_ms = convert_string_to_unix_time(self.last_time + "Z")


class Watchlist(BaseModel):
    def __init__(self, raw_data: Dict, name: str, watchlist_id: str) -> None:
        super(Watchlist, self).__init__(raw_data)
        self.name = name
        self.watchlist_id = watchlist_id


class AdvancedQueryResult(BaseModel):
    def __init__(self, raw_data: dict) -> None:
        super(AdvancedQueryResult, self).__init__(raw_data)
