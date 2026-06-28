# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import uuid
import re
from dateutil.parser import parse
from pytz import UTC
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, unix_now
from datetime import datetime
from dateutil.relativedelta import relativedelta
from splunk.core.constants import (
    DEFAULT_ALERT_NAME,
    TIME_UNIT_MAPPER,
    SEVERITY_MAPPER,
    DEFAULT_DEVICE_VENDOR,
    DEFAULT_DEVICE_PRODUCT,
    SPLUNK_EVENT_TYPE,
)
from TIPCommon.transformation import flat_dict_to_csv, dict_to_flat
from splunk.core.UtilsManager import convert_to_single_value_combinations

DETECT_VAR_PATTERN = r"\$(\S[^\$]*?)\|s\$"
DETECT_RAW_VAR_PATTERN = r"\$(\S[^\$]*?)(?<!\|s)\$"


class BaseModel:
    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self):
        return dict_to_flat(self.to_json())

    def to_csv(self):
        return flat_dict_to_csv(self.to_flat())

    def is_empty(self):
        return not bool(self.raw_data)


class JobDetail(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def to_filtered_csv(self, fields):
        if fields:
            fields = [field.strip() for field in fields.split(",") if field]
            csv_output = {}
            for key in fields:
                if self.raw_data.get(key):
                    csv_output[key] = self.raw_data[key]
            return csv_output or self.raw_data

        return self.raw_data

    @classmethod
    def from_json(cls, raw_data):
        return cls(raw_data=raw_data)


class SiemplifyCase(BaseModel):
    def __init__(
        self,
        raw_data,
        ticket_id,
        display_id,
        name,
        device_vendor,
        device_product,
        start_time,
        end_time,
        priority,
        events,
        rule_generator,
        description,
    ):
        super().__init__(raw_data)
        self.ticket_id = ticket_id
        self.display_id = display_id
        self.name = name
        self.device_vendor = device_vendor
        self.device_product = device_product
        self.start_time = start_time
        self.end_time = end_time
        self.priority = priority
        self.events = events
        self.rule_generator = rule_generator
        self.description = description


class SiemplifyAlert(BaseModel):
    def __init__(self, raw_data, alert_id, time, start_time, case):
        super().__init__(raw_data)
        self.case = case
        self.alert_id = alert_id
        self.timestamp = convert_datetime_to_unix_time(parse(time))
        self.original_datetime = parse(time)
        self.utc_time = parse(time).astimezone(UTC)
        self.unix_time = convert_datetime_to_unix_time(self.utc_time)


class SiemplifyEvent(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def as_alert_info(self):
        return dict_to_flat(self.raw_data)


class NotableEvent(BaseModel):
    def __init__(
        self,
        raw_data,
        event_id,
        count,
        search_name,
        rule_description,
        savedsearch_description,
        urgency,
        rule_name,
        earliest_time,
        latest_time,
        time,
        timestamp,
        orig_sid,
        info_max_time,
        info_min_time,
        info_search_time,
        comments,
        status,
        drilldown_search,
        drilldown_latest,
        drilldown_earliest,
        drilldown_latest_offset,
        drilldown_earliest_offset,
        rule_title,
    ):
        super().__init__(raw_data)
        self.original_raw_data = raw_data.copy()
        self.event_id = event_id
        self.count = count
        self.uuid = str(uuid.uuid4())
        self.search_name = search_name
        self.rule_description = (
            self.find_and_replace(rule_description) if rule_description else ""
        )
        self.savedsearch_description = savedsearch_description
        self.urgency = urgency
        self.rule_name = rule_name
        self.rule_title = rule_title
        self.earliest_time = earliest_time
        self.latest_time = latest_time
        self.time = time
        self.timestamp = timestamp
        if self.timestamp is not None:
            self.timestamp_ms = round(float(timestamp) * 1000)
        else:
            self.timestamp_ms = self.timestamp

        self.orig_sid = orig_sid
        self.job_details = None
        # start min max times
        self.info_max_time = info_max_time
        self.info_min_time = info_min_time
        self.valid_info_min_time = 0
        self.valid_info_max_time = 0
        self.is_max_and_min_time_available = False
        self._set_valid_min_max_times()
        # end min max times
        self.info_search_time = (
            int(str(info_search_time).split(".")[0]) if info_search_time else 0
        )
        self.source_events_start_time = 0
        self.source_events_end_time = 0
        self.set_source_events_start_end_times()
        self.comments = comments
        self.status = status
        self.drilldown_earliest = drilldown_earliest
        self.drilldown_latest = drilldown_latest
        self.drilldown_search = drilldown_search
        self.drilldown_earliest_offset = drilldown_earliest_offset
        self.drilldown_latest_offset = drilldown_latest_offset

    def find_and_replace(self, text):
        try:
            regex_match = r"\$(.*?)\$"
            matches = re.findall(regex_match, text)
            for key in matches:
                if self.raw_data.get(key):
                    try:
                        replace_with = (
                            ", ".join(self.raw_data[key])
                            if isinstance(self.raw_data[key], list)
                            else self.raw_data[key]
                        )
                        regex_replace = f"\${key}\$"
                        try:
                            text = re.sub(regex_replace, replace_with, text)
                        except:
                            # in some cases regex raise exception
                            # we need to try
                            text = text.replace(regex_replace, replace_with)
                    except:
                        pass
        except:
            pass
        return text

    def replace_single_variable(self, string_with_variable):
        try:
            matches_variables = re.findall(DETECT_VAR_PATTERN, string_with_variable)
            matches_row_variables = re.findall(
                DETECT_RAW_VAR_PATTERN, string_with_variable
            )
            matches = set(matches_variables + matches_row_variables)

            if not matches:
                return string_with_variable
            for match in matches:
                variable_value = self.original_raw_data.get(match)
                if variable_value:
                    string_with_variable = string_with_variable.replace(
                        f"${match}|s$", f'"{variable_value}"'
                    )
                    string_with_variable = string_with_variable.replace(
                        f"${match}$", f"{variable_value}"
                    )
        except:
            pass
        return string_with_variable

    def replace_splunk_variables(self, original_dict):
        result = {}
        for key, value in original_dict.items():
            result[key] = self.replace_single_variable(value)

        return result

    def get_drilldown_event_queries(self, logger=None):
        if not self.drilldown_search:
            logger.info("drilldown_search is empty. Skipping")
            return []

        logger.info(
            f'Drilldown_search is "{self.drilldown_search}" for alert "{self.event_id}"'
        )
        queries = []
        matches_variables = re.findall(DETECT_VAR_PATTERN, self.drilldown_search)
        matches_row_variables = re.findall(
            DETECT_RAW_VAR_PATTERN, self.drilldown_search
        )
        matches = set(matches_variables + matches_row_variables)
        variable_values = {}
        if not matches:
            return [self.drilldown_search]
        for match in matches:
            values = self.raw_data.get(match)
            if not values:
                logger.info(f'drilldown_search variable "{match}" does not have value')
                return []

            variable_values[match] = values if isinstance(values, list) else [values]

        logger.info(f"drilldown_search variables are {variable_values}")
        for combination in convert_to_single_value_combinations(variable_values):
            current_query = self.drilldown_search
            for variable, value in combination.items():
                current_query = current_query.replace(f"${variable}|s$", f'"{value}"')
                current_query = current_query.replace(f"${variable}$", f"{value}")
            queries.append(current_query)

        return queries

    def get_metadata_static_with_values(self):
        metadata_static_with_values = {}
        for key in self.job_details.field_metadata_static:
            value = self.raw_data.get(key)
            if value:
                metadata_static_with_values[key] = (
                    value if isinstance(value, list) else [value]
                )
        return metadata_static_with_values

    def set_job_details(self, job_details):
        self.job_details = job_details
        self.set_source_events_start_end_times()

    def _set_valid_min_max_times(self):
        try:
            self.valid_info_min_time = int(self.info_min_time.split(".")[0])
            self.valid_info_max_time = int(self.info_max_time.split(".")[0])
            if self.valid_info_min_time > 0 and self.valid_info_max_time > 0:
                self.is_max_and_min_time_available = True
        except Exception:
            pass

    def clean_event_data(self, event):
        unique_keys = []
        duplicate_keys = []
        for k in event.keys():
            if k.lower() in unique_keys:
                duplicate_keys.append(k)
            else:
                unique_keys.append(k.lower())
        for duplicate in duplicate_keys:
            event.pop(duplicate, None)
        return event

    def prepare_events(self, events, drilldown_events=False):
        if drilldown_events:
            for event in events:
                event["chronicle_soar_fallback_indextime"] = self.raw_data.get(
                    "_indextime"
                )

        return [
            self.replace_splunk_variables(dict_to_flat(self.clean_event_data(event)))
            for event in events
        ]

    def get_alert_as_event(self, exclude_keys=None, set_drilldown_fields=False):
        exclude_keys = exclude_keys or []
        self.raw_data["startTime"] = self.get_start_time()
        self.raw_data["endTime"] = self.get_end_time()
        if self.is_max_and_min_time_available:
            self.raw_data["info_min_time"] = self.valid_info_min_time * 1000
            self.raw_data["info_max_time"] = self.valid_info_max_time * 1000
        else:
            if self.raw_data.get("info_min_time") is not None:
                del self.raw_data["info_min_time"]
            if self.raw_data.get("info_max_time") is not None:
                del self.raw_data["info_max_time"]
        self.raw_data["info_search_time"] = self.info_search_time * 1000
        self.raw_data["rule_description"] = self.rule_description

        if set_drilldown_fields:
            if self.drilldown_earliest_offset:
                self.raw_data["drilldown_earliest_offset"] = self.find_and_replace(
                    self.drilldown_earliest_offset
                )

            if self.drilldown_latest_offset:
                self.raw_data["drilldown_latest_offset"] = self.find_and_replace(
                    self.drilldown_latest_offset
                )

        for exclude_key in exclude_keys:
            if self.raw_data.get(exclude_key):
                del self.raw_data[exclude_key]

        return self.replace_splunk_variables(
            dict_to_flat(self.clean_event_data(self.raw_data))
        )

    def get_updated_event(self, new_fields):
        return self.replace_splunk_variables(
            dict_to_flat(
                dict(
                    self.get_alert_as_event(exclude_keys=list(set(new_fields.keys()))),
                    **new_fields,
                )
            )
        )

    def get_multi_value_fields(self, keys):
        multi_values = {}
        for key in keys:
            value = self.raw_data.get(key)
            if isinstance(value, list):
                multi_values[key] = value
        return multi_values

    def is_query_available(self):
        if not self.job_details:
            return False

        if not self.job_details.query_to_execute:
            return False

        return True

    def is_source_events_available(self):
        if not self.is_query_available():
            return False

        if not self.source_events_end_time or not self.source_events_start_time:
            return False

        return True

    def set_source_events_start_end_times(self):
        if self.is_max_and_min_time_available:
            self.source_events_start_time = self.valid_info_min_time
            self.source_events_end_time = self.valid_info_max_time
        elif self.job_details:
            try:
                self.source_events_start_time = (
                    self.job_details.calculate_source_events_start_time(
                        self.info_search_time
                    )
                )
                self.source_events_end_time = (
                    self.job_details.calculate_source_events_end_time(
                        self.info_search_time
                    )
                )
            except Exception as e:
                pass

    def get_alert_info(
        self,
        alert_info,
        environment_common,
        alert_name_source,
        rule_generator_field_name,
    ):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.event_id
        alert_info.display_id = self.event_id
        alert_name = getattr(self, alert_name_source)
        alert_info.name = self.replace_single_variable(alert_name) or DEFAULT_ALERT_NAME
        alert_info.reason = self.replace_single_variable(self.rule_description)
        alert_info.description = self.replace_single_variable(
            self.savedsearch_description
        )
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = DEFAULT_DEVICE_PRODUCT
        alert_info.priority = self.get_siemplify_severity()
        rule_generator = self.replace_single_variable(
            self.original_raw_data.get(rule_generator_field_name, None)
        )
        if rule_generator and isinstance(rule_generator, str):
            rule_generator = (
                (rule_generator[:254] + "..")
                if len(rule_generator) > 256
                else rule_generator
            )
        alert_info.rule_generator = rule_generator or self.replace_single_variable(
            self.rule_name
        )
        alert_info.start_time = self.get_start_time()
        alert_info.end_time = self.get_end_time()
        alert_info.extensions = {"splunk_event_type": SPLUNK_EVENT_TYPE}

        return alert_info

    def get_start_time(self):
        return 1000 * (
            self.source_events_start_time
            if (self.source_events_start_time and self.source_events_end_time)
            else self.info_search_time
        )

    def get_end_time(self):
        return 1000 * (
            self.source_events_end_time
            if (self.source_events_start_time and self.source_events_end_time)
            else self.info_search_time
        )

    def get_siemplify_severity(self):
        siemplify_severity = -1
        for key, value in sorted(SEVERITY_MAPPER.items()):
            if value.lower() == self.urgency.lower():
                siemplify_severity = key
                break

        return siemplify_severity

    def to_log(self):
        return (
            "is_max_and_min_time_available: {is_max_and_min_time_available} "
            "| info_max_time: {info_max_time}"
            "| info_min_time: {info_min_time}"
            "| valid_info_min_time: {valid_info_min_time}"
            "| valid_info_max_time: {valid_info_max_time}"
            "| info_search_time: {info_search_time}"
            "| source_events_start_time: {source_events_start_time}"
            "| source_events_end_time: {source_events_end_time}"
            "| job_details: {job_details}".format(
                is_max_and_min_time_available=self.is_max_and_min_time_available,
                info_max_time=self.info_max_time,
                info_min_time=self.info_min_time,
                valid_info_min_time=self.valid_info_min_time,
                valid_info_max_time=self.valid_info_max_time,
                info_search_time=self.info_search_time,
                source_events_start_time=self.source_events_start_time,
                source_events_end_time=self.source_events_end_time,
                job_details=self.job_details.to_log() if self.job_details else "",
            )
        )


class NotableEventSearchResult:
    def __init__(self, preview, event):
        self.preview = preview
        self.event = event


class JobDetails(BaseModel):
    def __init__(
        self, raw_data, name, earliest_time, latest_time, field_metadata_static
    ):
        super().__init__(raw_data)
        self.query_to_execute = name
        self.earliest_time = earliest_time
        self.latest_time = latest_time
        self.field_metadata_static = field_metadata_static

    def calculate_source_events_start_time(self, info_search_time):
        return self.calculate_diff(info_search_time, self.earliest_time)

    def calculate_source_events_end_time(self, info_search_time):
        return self.calculate_diff(info_search_time, self.latest_time)

    def calculate_diff(self, info_search_time, delta):
        info_search_time = datetime.fromtimestamp(info_search_time)
        if delta.lower() == "now":
            return int(unix_now() / 1000)

        # make rt-5m@m to -5m@m
        delta = delta.replace("rt", "")
        # make 5m@m to -5m
        delta = delta.split("@")[0]
        value, unit = re.findall(r"([\-\+]?\d*)(\w*)", delta)[0]
        value = int(value)
        if unit == "y":
            unit = "mon"
            value = 12 * value
        elif unit == "q":
            unit = "mon"
            value = 3 * value
        date = info_search_time + relativedelta(**{TIME_UNIT_MAPPER[unit]: value})
        date = date.replace(tzinfo=UTC)
        return int(convert_datetime_to_unix_time(date) / 1000)

    def to_log(self):
        return (
            "query_to_execute_len: {query_to_execute_len} "
            "| earliest_time: {earliest_time}"
            "| latest_time: {latest_time}"
            "| field_metadata_static: {field_metadata_static}".format(
                query_to_execute_len=len(self.query_to_execute),
                earliest_time=self.earliest_time,
                latest_time=self.latest_time,
                field_metadata_static="|".join(self.field_metadata_static),
            )
        )


class SourceEvent(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)


class Event(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)

    def to_csv(self, fields=None):
        if fields:
            fields = [field.strip() for field in fields.split(",") if field]
            csv_output = {}
            for key in fields:
                if self.raw_data.get(key):
                    csv_output[key] = self.raw_data[key]
            return csv_output or self.raw_data

        return self.raw_data


class QueryEvent(BaseModel):
    def __init__(self, raw_data, time, query, event_id):
        super().__init__(raw_data)
        self.date = parse(time)
        self.timestamp = int(self.date.timestamp() * 1000)
        self.event_id = event_id
        self.query = query

    def to_json(self):
        raw_data = super().to_json()
        raw_data.update({"starttime_unixtime": self.timestamp})
        return raw_data
