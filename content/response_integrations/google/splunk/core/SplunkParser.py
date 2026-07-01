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
import json
from ..core.datamodels import *
from ..core.constants import MAX_EVENTS_COUNT


class SplunkParser:
    def build_siemplify_alert_list_from_result_json(self, result_json):
        cases = self.extruct_cases_data_from_result_json(result_json)
        case = None
        if cases:
            case = self.build_siemplify_case_from_case_json(cases[0])

        return SiemplifyAlert(
            raw_data=result_json,
            alert_id=result_json.get("_key", ""),
            time=result_json.get("_time", ""),
            start_time=case.start_time,
            case=case,
        )

    def build_siemplify_case_from_case_json(self, case_json):
        return SiemplifyCase(
            raw_data=case_json,
            ticket_id=case_json.get("TicketId"),
            display_id=case_json.get("DisplayId"),
            name=case_json.get("Name"),
            device_vendor=case_json.get("DeviceVendor"),
            device_product=case_json.get("DeviceProduct"),
            start_time=case_json.get("StartTime", 1),
            end_time=case_json.get("EndTime", 1),
            priority=case_json.get("Priority"),
            events=[
                self.build_siemplify_event(event_json)
                for event_json in case_json.get("Events", [])
            ],
            rule_generator=case_json.get("RuleGenerator"),
            description=case_json.get("Description"),
        )

    def build_siemplify_event(self, event_json):
        return SiemplifyEvent(raw_data=event_json)

    def extruct_cases_data_from_result_json(self, result_json):
        try:
            case_data_json = json.loads(result_json.get("case_data", {}))
        except ValueError:
            case_data_json = {}

        cases = case_data_json.get("Cases", [])
        return cases

    def build_notable_event_object(self, notable_event_json):
        return NotableEvent(
            raw_data=notable_event_json,
            event_id=notable_event_json.get("event_id"),
            count=notable_event_json.get("count", MAX_EVENTS_COUNT),
            search_name=notable_event_json.get("search_name"),
            rule_description=notable_event_json.get("rule_description"),
            savedsearch_description=notable_event_json.get("savedsearch_description"),
            urgency=notable_event_json.get("urgency"),
            rule_name=notable_event_json.get("rule_name"),
            earliest_time=notable_event_json.get("epoch"),
            latest_time=notable_event_json.get("epoch"),
            time=notable_event_json.get("_time"),
            timestamp=notable_event_json.get("epoch"),
            orig_sid=notable_event_json.get("orig_sid"),
            info_max_time=notable_event_json.get("info_max_time"),
            info_min_time=notable_event_json.get("info_min_time"),
            info_search_time=notable_event_json.get("info_search_time"),
            comments=self.build_comments_list(notable_event_json.get("comment")),
            status=notable_event_json.get("status"),
            drilldown_search=notable_event_json.get("drilldown_search"),
            drilldown_earliest=notable_event_json.get("drilldown_earliest"),
            drilldown_latest=notable_event_json.get("drilldown_latest"),
            drilldown_latest_offset=notable_event_json.get("drilldown_latest_offset"),
            drilldown_earliest_offset=notable_event_json.get(
                "drilldown_earliest_offset"
            ),
            rule_title=notable_event_json.get("rule_title"),
        )

    def build_comments_list(self, comments):
        if comments:
            if isinstance(comments, list):
                return comments
            return [comments]

    def get_event_from_search_result(self, raw_json, is_notable=True):
        result_json = raw_json.get("result")
        if result_json:
            return NotableEventSearchResult(
                preview=raw_json.get("preview"),
                event=(
                    self.build_notable_event_object(result_json)
                    if is_notable
                    else self.build_source_event(result_json)
                ),
            )

    def build_source_event(self, raw_json):
        return SourceEvent(raw_data=raw_json)

    def build_event(self, raw_json):
        return Event(raw_data=raw_json)

    def build_query_event(self, raw_json, query=None):
        if not raw_json:
            return []

        return QueryEvent(
            raw_data=raw_json,
            query=query,
            event_id=raw_json.get("_cd"),
            time=raw_json.get("_time"),
        )

    def build_job_details_object(self, raw_json):
        entry_json = self.get_first_entry(raw_json)
        if entry_json:
            # changed to event_search to name
            return JobDetails(
                raw_data=entry_json,
                name=entry_json.get("name"),
                earliest_time=entry_json.get("content", {})
                .get("request", {})
                .get("earliest_time"),
                latest_time=entry_json.get("content", {})
                .get("request", {})
                .get("latest_time"),
                field_metadata_static=list(
                    entry_json.get("content", {}).get("fieldMetadataStatic", {})
                ),
            )

    def build_results(self, raw_json, method_name=None):
        results = raw_json.get("results", [])
        return (
            [getattr(self, method_name)(result_json) for result_json in results]
            if method_name
            else results
        )

    def build_result(self, raw_json, method_name=None):
        result = raw_json.get("result", [])
        if result:
            return getattr(self, method_name)(result) if method_name else result

    def build_job_detail_model(self, raw_json):
        return JobDetail(raw_json)

    def extract_error_message(self, error_json):
        default_error_msg = "Error message is not available"
        msg = error_json.get("messages")
        if msg and isinstance(msg, list):
            return msg[0].get("text", default_error_msg)
        return default_error_msg

    def get_sid_from_search(self, raw_json):
        return raw_json.get("sid", "")

    def get_first_entry(self, raw_json):
        return raw_json.get("entry", [{}])[0]

    def get_content_from_entry_json(self, entry_json):
        return entry_json.get("content", {})

    def get_is_done_status(self, raw_json):
        return self.get_content_from_entry_json(self.get_first_entry(raw_json)).get(
            "isDone", False
        )
