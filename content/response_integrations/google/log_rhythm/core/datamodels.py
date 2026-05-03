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
import copy
import json
import uuid
from datetime import datetime

from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time, convert_string_to_unix_time
from TIPCommon import dict_to_flat, add_prefix_to_dict
from .constants import (
    REST_ALARMS_DATE_FORMAT,
    INFO_SIEMPLIFY_SEVERITY,
    LOW_SIEMPLIFY_SEVERITY,
    MEDIUM_SIEMPLIFY_SEVERITY,
    HIGH_SIEMPLIFY_SEVERITY,
    CRITICAL_SIEMPLIFY_SEVERITY,
    DEFAULT_DEVICE_PRODUCT,
    DEVICE_VENDOR,
    DEFAULT_ALERT_NAME,
    CASE_TYPE,
    PRIORITY_MAPPING,
    EVIDENCE_TYPE,
    PIFTypes_MAPPING,
)
from .utils import convert_naive_datetime_to_aware_utc


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data: dict):
        self.raw_data = raw_data

    def as_json(self):
        return self.raw_data

    def as_csv(self):
        return dict_to_flat(self.as_json())

    def as_flat(self):
        return dict_to_flat(self.raw_data)

    def as_enrichment(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class AlarmSummaryDetails(BaseModel):
    """
    Alarm Summary Details data model
    """

    def __init__(
        self,
        raw_data,
        date_inserted=None,
        alarm_rule_id=None,
        alarm_rule_group=None,
        brief_description=None,
    ):
        super().__init__(raw_data)
        self.date_inserted = date_inserted
        self.alarm_rule_id = alarm_rule_id
        self.alarm_rule_group = alarm_rule_group
        self.brief_description = brief_description


class Alarm(BaseModel):
    """
    Alarm Search Details data model
    """

    def __init__(
        self,
        raw_data,
        alarm_id=None,
        alarm_rule_name=None,
        alarm_status=None,
        entity_name=None,
        date_inserted=None,
    ):
        super().__init__(raw_data)
        self.alarm_id = alarm_id
        self.alarm_rule_name = alarm_rule_name
        self.alarm_status = alarm_status
        self.entity_name = entity_name
        self.date_inserted = date_inserted
        try:
            self.timestamp = convert_datetime_to_unix_time(
                convert_naive_datetime_to_aware_utc(
                    datetime.strptime(self.date_inserted, REST_ALARMS_DATE_FORMAT)
                )
            )
        except:
            self.timestamp = 1

    def get_alert_info(
        self,
        alert_info,
        device_product_field,
        environment_common,
        alarm_summary_details,
        events,
    ):
        """
        Generate AlertInfo() object from Alarm's data
        :param alert_info: {AlertInfo} AlertInfo instance
        :param device_product_field: {str} Device product field
        :param environment_common: {EnvironmentHandle} EnvironmentHandle obejct
        :param alarm_summary_details: {AlarmSummaryDetails} Alarm's summary details
        :param events: {[AlarmEventDetails]} List of alarm's events
        :return: {AlertInfo} AlertInfo representing Siemplify Alert
        """
        alert_info.ticket_id = self.alarm_id
        alert_info.display_id = self.alarm_id
        alert_info.name = self.alarm_rule_name
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = self.as_flat().get(
            device_product_field, DEFAULT_DEVICE_PRODUCT
        )
        alert_info.priority = self.get_siemplify_severity(events)
        alert_info.rule_generator = self.alarm_rule_name
        alert_info.end_time = alert_info.start_time = self.timestamp
        alert_info.events = self.create_events(events)

        environment_dict = self.as_flat()
        if alert_info.events:
            environment_dict.update(alert_info.events[0])

        if alarm_summary_details and isinstance(
            alarm_summary_details, AlarmSummaryDetails
        ):
            alert_info.description = alarm_summary_details.brief_description
            alert_info.extensions = alarm_summary_details.as_flat()
            environment_dict.update(alarm_summary_details.as_flat())

        alert_info.environment = environment_common.get_environment(environment_dict)

        return alert_info

    def get_siemplify_severity(self, events):
        """
        Get Siemplify alert severity correlated to alarm's severity
        :param events: {[AlarmEventDetails]} List of alarm's events
        :return: {int} Numeric value of Siemplify's alert
        """
        priority = (
            max(event.priority for event in events if isinstance(event.priority, int))
            if events
            else -1
        )
        if 0 <= priority <= 40:
            return LOW_SIEMPLIFY_SEVERITY
        elif 41 <= priority <= 60:
            return MEDIUM_SIEMPLIFY_SEVERITY
        elif 61 <= priority <= 80:
            return HIGH_SIEMPLIFY_SEVERITY
        elif 81 <= priority <= 100:
            return CRITICAL_SIEMPLIFY_SEVERITY
        else:
            return INFO_SIEMPLIFY_SEVERITY

    def create_events(self, events):
        """
        Create Siemplify events
        :param events: {[AlarmEventDetails]} List of alarm's events
        :return: {[dict]} List of flattened dictionaries
        """
        if not events:
            return [self.as_flat()]
        return [event.as_event() for event in events]


class AlarmEventDetails(BaseModel):
    """
    Alarm's event details data model
    """

    def __init__(
        self,
        raw_data,
        classification_name=None,
        classification_type=None,
        name=None,
        priority=None,
        account=None,
        hostname=None,
        log_date=None,
    ):
        super(AlarmEventDetails, self).__init__(raw_data)
        self.priority = priority
        self.log_date = log_date
        self.classification_name = classification_name
        self.classification_type = classification_type
        self.name = name
        self.account = account
        self.hostname = hostname
        try:
            self.event_timestamp = convert_datetime_to_unix_time(
                convert_naive_datetime_to_aware_utc(
                    datetime.strptime(self.log_date, REST_ALARMS_DATE_FORMAT)
                )
            )
        except:
            self.event_timestamp = 1

    def as_event(self):
        raw_flatten_event = dict_to_flat(self.raw_data)
        raw_flatten_event.update({"event_timestamp": self.event_timestamp})
        return raw_flatten_event

    def to_csv(self):
        return {
            "Classification Name": self.classification_name,
            "Classification Type": self.classification_type,
            "Name": self.name,
            "Priority": self.priority,
            "Account": self.account,
            "Hostname": self.hostname,
        }


class EntityDetails(BaseModel):
    def __init__(
        self,
        raw_data,
        description=None,
        risk_level=None,
        threat_level=None,
        status=None,
        host_zone=None,
        os_version=None,
        type=None,
        name=None,
        host_identifiers=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.description = description
        self.risk_level = risk_level
        self.threat_level = threat_level
        self.status = status
        self.host_zone = host_zone
        self.os = os_version
        self.type = type
        self.name = name
        self.host_identifiers = host_identifiers
        self.ips = self.get_ip_addresses() if self.host_identifiers else None

    def as_enrichment_data(self):
        enrichment_data = {
            "description": self.description,
            "risk_level": self.risk_level,
            "threat_level": self.threat_level,
            "status": self.status,
            "host_zone": self.host_zone,
            "os": self.os,
            "type": self.type,
            "ips": self.ips,
        }
        enrichment_data = {k: v for k, v in enrichment_data.items() if v is not None}

        return dict_to_flat(enrichment_data)

    def as_table_data(self):
        table_data = {
            "description": self.description,
            "risk_level": self.risk_level,
            "threat_level": self.threat_level,
            "status": self.status,
            "host_zone": self.host_zone,
            "os": self.os,
            "type": self.type,
            "ips": self.get_ip_addresses(delimiter="; "),
        }
        enrichment_data = {k: v for k, v in table_data.items() if v is not None}

        return dict_to_flat(enrichment_data)

    def to_insight(self):
        return (
            f'<h3><strong>Risk Level: {self.risk_level or ""}&nbsp;</strong><strong>'
            f'Threat Level: {self.threat_level or ""}</strong></h3><p><strong>Name: </strong>{self.name or ""}<br />'
            f'<strong>Status: </strong>{self.status or ""}<strong><br />OS Type: </strong>{self.type or ""}'
            f'<strong><br />OS Version: </strong>{self.os or ""}<strong><br /></strong><strong>Zone: </strong>'
            f'{self.host_zone or ""}<strong><br /></strong><strong>Description: </strong>{self.description or ""}'
            f"<strong><br /></strong></p><p>&nbsp;</p>"
        )

    def get_ip_addresses(self, delimiter=", "):
        ips = [
            identifier.value
            for identifier in self.host_identifiers
            if identifier.type == "IPAddress"
        ]

        return delimiter.join(ips)


class HostIdentifiers(BaseModel):
    def __init__(self, raw_data, type=None, value=None, **kwargs):
        super().__init__(raw_data)
        self.type = type
        self.value = value


class CaseNote(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)


class CaseAlarm(BaseModel):
    def __init__(self, raw_data):
        super().__init__(raw_data)


class AlarmDetails(BaseModel):
    def __init__(self, raw_data, status=None, **kwargs):
        super().__init__(raw_data)
        self.status = status

    def to_json(self, alarm_events, drilldown_data=None):
        data = self.raw_data
        data.update(
            {
                "alarmEventsDetails": [
                    alarm_event.as_json() for alarm_event in alarm_events
                ]
            }
        )
        if drilldown_data:
            data.update({"DrillDownResults": drilldown_data.as_json()})

        return data


class CaseEvidence(BaseModel):
    def __init__(
        self,
        raw_data,
        number=None,
        status=None,
        evidence_type=None,
        context=None,
        date_created=None,
        filename=None,
        filesize=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.id = number
        self.status = status
        self.evidence_type = evidence_type
        self.context = context
        self.filename = filename
        self.filesize = filesize
        self.date_created = date_created

    def to_csv(self):
        return {
            "Type": self.evidence_type,
            "Status": self.status,
            "Context": self.context,
        }


class Case(BaseModel):
    def __init__(self, raw_data, number=None, status_name=None, **kwargs):
        super().__init__(raw_data)
        self.number = number
        self.status = status_name


class Task(BaseModel):
    def __init__(self, raw_data, id=None, status=None, events=None):
        super().__init__(raw_data)
        self.id = id
        self.status = status
        self.events = events


class Event(BaseModel):
    def __init__(
        self,
        raw_data,
        classification=None,
        event_name=None,
        date=None,
        impacted_host=None,
        impacted_ip=None,
        hash=None,
        url=None,
        priority=None,
        cve=None,
        origin_host=None,
        origin_ip=None,
        login=None,
    ):
        super().__init__(raw_data)
        self.classification = classification
        self.event_name = event_name
        self.date = datetime.fromtimestamp(int(date / 1000)).isoformat()
        self.impacted_host = impacted_host
        self.impacted_ip = impacted_ip
        self.hash = hash
        self.url = url
        self.priority = priority
        self.cve = cve
        self.origin_host = origin_host
        self.origin_ip = origin_ip
        self.login = login

    def to_csv(self):
        data = {
            "Classification": self.classification,
            "Event Name": self.event_name,
            "Date": self.date,
            "Impacted Host": self.impacted_host,
            "Impacted IP": self.impacted_ip,
            "Login": self.login,
            "Hash": self.hash,
            "URL": self.url,
            "Priority": self.priority,
            "CVE": self.cve,
            "Origin Host": self.origin_host,
            "Origin IP": self.origin_ip,
        }
        data = {key: value for key, value in data.items() if value is not None}

        return data


class AlarmComment(BaseModel):
    def __init__(self, raw_data, comments=None, date=None):
        super().__init__(raw_data)
        self.comments = comments
        self.date = date


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        id=None,
        number=None,
        dateCreated=None,
        dateClosed=None,
        name=None,
        priority=None,
        summary=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.id = id
        self.number = number
        self.date_created = dateCreated if dateCreated else "1"
        self.date_closed = dateClosed if dateClosed else "1"
        self.name = name
        self.priority = priority
        self.summary = summary

    def as_flat_event(self):
        data = self.raw_data
        data.update({"event_type": CASE_TYPE})
        return dict_to_flat(data)

    def as_flat_extension(self):
        data = copy.deepcopy(self.raw_data)
        if data.get("priority"):
            data.pop("priority")
        return dict_to_flat(data)

    def create_case_info(self, case_info, product_field_name, environment_common):
        """
        Create CaseInfo object from LogRhythm alert
        :param case_info: {CaseInfo} Case Info obj
        :param product_field_name: {srt} Product field name
        :param environment_common: {str} Environment Handler instance
        :return: {CaseInfo} The newly created case
        """
        case_info.name = self.name or DEFAULT_ALERT_NAME
        case_info.ticket_id = self.number
        case_info.display_id = str(uuid.uuid4())
        case_info.description = self.summary

        case_info.rule_generator = self.name or "Unable to get LogRhythm alert name"
        case_info.device_vendor = DEVICE_VENDOR
        case_info.device_product = self.raw_data.get(
            product_field_name, DEFAULT_DEVICE_PRODUCT
        )
        case_info.environment = environment_common.get_environment(self.raw_data)
        case_info.priority = self.get_priority()
        case_info.start_time = convert_string_to_unix_time(self.date_created)
        case_info.end_time = convert_string_to_unix_time(self.date_created)
        case_info.extensions = self.as_flat_extension()
        case_info.events = [self.as_flat_event()]

        return case_info

    def get_priority(self):
        return PRIORITY_MAPPING.get(str(self.priority), -1)


class SiemplifyEvent(BaseModel):
    def __init__(self, raw_data, **kwargs):
        super().__init__(raw_data)

    def as_flat_event(self):
        data = self.raw_data
        data.update({"event_type": EVIDENCE_TYPE})
        return dict_to_flat(data)


class AlarmDrilldown(BaseModel):
    def __init__(self, raw_data: dict, rule_blocks: list = None):
        super().__init__(raw_data)
        self.rule_blocks = rule_blocks
        self.parse_rule_blocks()

    def parse_rule_blocks(self) -> None:
        """
        Parses LogRhythm Alarm DrillDown data, extracts string-represented JSON

        Returns:
            None
        """
        if self.rule_blocks:
            dd_summaries_key = "DDSummaries"
            drill_down_logs_key = "DrillDownLogs"
            for rule_block in self.rule_blocks:
                if drill_down_logs_key in rule_block:
                    rule_block[drill_down_logs_key] = json.loads(
                        rule_block[drill_down_logs_key]
                    )
                if dd_summaries_key in rule_block:
                    for dd_summary in rule_block[dd_summaries_key]:
                        dd_summary["DrillDownSummaryLogs"] = json.loads(
                            dd_summary["DrillDownSummaryLogs"]
                        )

                        if dd_summary["DrillDownSummaryLogs"]:
                            pif_type = dd_summary["PIFType"]
                            dd_summary[PIFTypes_MAPPING[pif_type].get("Field Name")] = (
                                dd_summary["DrillDownSummaryLogs"][0].get("field")
                            )
