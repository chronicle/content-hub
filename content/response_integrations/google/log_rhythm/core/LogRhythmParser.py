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
from .datamodels import (
    Alarm,
    AlarmSummaryDetails,
    AlarmEventDetails,
    EntityDetails,
    HostIdentifiers,
    AlarmDetails,
    CaseNote,
    CaseAlarm,
    CaseEvidence,
    Task,
    Event,
    Case,
    AlarmComment,
    Alert,
    SiemplifyEvent,
    AlarmDrilldown,
)

FILE = "file"
NOTE = "note"
ALARM = "alarm"


class LogRhythmParser:
    def build_results(
        self, raw_json, method, data_key="data", pure_data=False, limit=None, **kwargs
    ):
        return [
            getattr(self, method)(item_json, **kwargs)
            for item_json in (
                raw_json if pure_data else raw_json.get(data_key, []) or []
            )[:limit]
        ]

    @staticmethod
    def build_alarm_obj(raw_alarm):
        return Alarm(
            raw_data=raw_alarm,
            alarm_id=raw_alarm.get("alarmId"),
            alarm_rule_name=raw_alarm.get("alarmRuleName"),
            alarm_status=raw_alarm.get("alarmStatus"),
            entity_name=raw_alarm.get("entityName"),
            date_inserted=raw_alarm.get("dateInserted"),
        )

    @staticmethod
    def build_alarm_summary_obj(raw_alarm_summary):
        raw_alarm_summary_details = (
            raw_alarm_summary.get("alarmSummaryDetails", {}) or {}
        )
        return AlarmSummaryDetails(
            raw_data=raw_alarm_summary_details,
            date_inserted=raw_alarm_summary_details.get("dateInserted"),
            alarm_rule_id=raw_alarm_summary_details.get("alarmRuleId"),
            alarm_rule_group=raw_alarm_summary_details.get("alarmRuleGroup"),
            brief_description=raw_alarm_summary_details.get("briefDescription"),
        )

    @staticmethod
    def build_alarm_event_details_obj_list(raw_events_response):
        return [
            LogRhythmParser.build_alarm_event_details_obj(raw_event)
            for raw_event in raw_events_response.get("alarmEventsDetails", [])
        ]

    @staticmethod
    def build_alarm_event_details_obj(raw_event):
        return AlarmEventDetails(
            raw_data=raw_event,
            classification_name=raw_event.get("classificationName"),
            classification_type=raw_event.get("classificationTypeName"),
            name=raw_event.get("commonEventName"),
            priority=raw_event.get("priority"),
            account=raw_event.get("account"),
            hostname=raw_event.get("impactedHostName"),
            log_date=raw_event.get("logDate"),
        )

    def build_entity_details_obj(self, raw_data):
        return EntityDetails(
            raw_data=raw_data,
            description=raw_data.get("shortDesc"),
            risk_level=raw_data.get("riskLevel"),
            threat_level=raw_data.get("threatLevel"),
            status=raw_data.get("recordStatusName"),
            host_zone=raw_data.get("hostZone"),
            os_version=raw_data.get("osVersion"),
            type=raw_data.get("osType"),
            host_identifiers=self.build_results(
                raw_json=raw_data.get("hostIdentifiers", []),
                method="build_host_identifiers_obj",
                pure_data=True,
            ),
            **raw_data
        )

    def build_host_identifiers_obj(self, raw_data):
        return HostIdentifiers(raw_data=raw_data, **raw_data)

    def build_alarm_details_obj(self, raw_data):
        raw_alarm_details = raw_data.get("alarmDetails", {}) or {}
        return AlarmDetails(
            raw_data=raw_alarm_details,
            status=raw_alarm_details.get("alarmStatusName", ""),
            **raw_alarm_details
        )

    def build_case_note_obj(self, raw_data):
        return CaseNote(raw_data=raw_data)

    def build_case_alarm_obj(self, raw_data):
        return CaseAlarm(raw_data=raw_data)

    def build_case_evidence_obj(self, raw_data):
        return CaseEvidence(
            raw_data=raw_data,
            evidence_type=raw_data.get("type", ""),
            date_created=raw_data.get("dateCreated", ""),
            context=self.build_evidence_context(raw_data),
            filename=raw_data.get("file", {}).get("name"),
            filesize=raw_data.get("file", {}).get("size"),
            **raw_data
        )

    def build_evidence_context(self, raw_data):
        if raw_data.get("type", "") == FILE:
            return raw_data.get(FILE, "").get("name", "")
        if raw_data.get("type", "") == NOTE:
            return raw_data.get("text", "")
        if raw_data.get("type", "") == ALARM:
            return raw_data.get(ALARM, "").get("alarmRuleName", "")

        return ""

    def build_task_obj(self, raw_data):
        return Task(
            raw_data=raw_data,
            id=raw_data.get("TaskId", ""),
            status=raw_data.get("TaskStatus", ""),
            events=self.build_results(raw_data, "build_event_obj", data_key="Items"),
        )

    def build_event_obj(self, raw_data):
        return Event(
            raw_data=raw_data,
            classification=raw_data.get("classificationName"),
            event_name=raw_data.get("commonEventName"),
            date=raw_data.get("insertedDate"),
            impacted_host=raw_data.get("impactedHost"),
            impacted_ip=raw_data.get("impactedIp"),
            hash=raw_data.get("hash"),
            url=raw_data.get("url"),
            priority=raw_data.get("priority"),
            cve=raw_data.get("cve"),
            origin_host=raw_data.get("originHost"),
            origin_ip=raw_data.get("originIp"),
            login=raw_data.get("login"),
        )

    def build_case_obj(self, raw_data):
        return Case(
            raw_data=raw_data,
            status_name=raw_data.get("status", {}).get("name"),
            **raw_data
        )

    def build_alarm_comments_obj(self, raw_data):
        return AlarmComment(
            raw_data=raw_data,
            comments=raw_data.get("comments", ""),
            date=raw_data.get("dateInserted", ""),
        )

    def build_siemplify_alert_obj(self, raw_data):
        return Alert(raw_data=raw_data, **raw_data)

    def build_siemplify_events_obj(self, raw_data):
        return SiemplifyEvent(raw_data=raw_data, **raw_data)

    @staticmethod
    def build_alarm_drilldown_obj(raw_data: dict) -> AlarmDrilldown:
        """
        Builds AlarmDrilldown object from given dictionary

        Args:
            raw_data: Data extracted from LogRhythm API

        Returns:
            AlarmDrilldown object with data
        """
        raw_alarm_drilldown = raw_data.get("Data", {}).get("DrillDownResults", {})
        return AlarmDrilldown(
            raw_data=raw_alarm_drilldown,
            rule_blocks=raw_alarm_drilldown.get("RuleBlocks"),
        )
