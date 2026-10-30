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

import dataclasses
import uuid
from abc import ABCMeta
from copy import deepcopy
from typing import Any, Optional

from EnvironmentCommon import EnvironmentHandleForDBSystem, EnvironmentHandle

from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time

from TIPCommon.base.connector.base_connector import BaseAlert
from TIPCommon.transformation import dict_to_flat, add_prefix_to_dict
from TIPCommon.types import SingleJson

from crowd_strike_falcon.core.constants import (
    ALERTS_CONNECTOR_SEVERITY_MAPPING,
    API_CLIENT_ID_KEY,
    APP_ID_KEY,
    AUTH_ACTIVITY_AUDIT_EVENT_TYPE,
    CHARACTERS_LIMIT,
    DEFAULT_ALERT_NAME,
    DEFAULT_DEVICE_VENDOR,
    DEFAULT_DEVICE_PRODUCT,
    DEFAULT_SEVERITY,
    DETECTION_EVENT_TYPE,
    ENRICHMENT_PREFIX,
    EventStatus,
    INCIDENTS_CONNECTOR_ALERT_DISPLAY_NAME_PREFIX,
    INCIDENTS_CONNECTOR_ALERT_DISPLAY_ID_PREFIX,
    INCIDENTS_CONNECTOR_DEVICE_VENDOR,
    INCIDENTS_CONNECTOR_DEVICE_PRODUCT,
    INCIDENTS_CONNECTOR_RULE_GENERATOR_PREFIX,
    INCIDENTS_CONNECTOR_SEVERITY_MAPPING,
    INFO_SEVERITY_NAME,
    INSIGHT_KEYS,
    INSIGHT_VALUES,
    OPEN,
    REMOTE_RESPONSE_SESSION_END_EVENT_TYPE,
    REMOTE_RESPONSE_SESSION_START_EVENT_TYPE,
    REOPEN,
    Severity,
    SEVERITY_MAP,
    SIEM_DETECTION_EVENT_TYPE,
    SIEM_AUTH_ACTIVITY_AUDIT_EVENT_TYPE,
    SIEM_USER_ACTIVITY_AUDIT_EVENT_TYPE,
    SIEM_REMOTE_RESPONSE_SESSION_EVENT_TYPE,
    SIEM_UNKNOWN_EVENT_TYPE,
    STREAM_STARTED,
    STREAM_STOPPED,
    USER_ACTIVITY_AUDIT_EVENT_TYPE,
)
from crowd_strike_falcon.core.utils import convert_list_to_comma_string, format_template

CROWD_STRIKE_TO_SIEM_PRIORITIES = {0: -1, 1: -1, 2: 40, 3: 60, 4: 80, 5: 100}


class BaseModel:
    def __init__(self, raw_data) -> None:
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_flat(self) -> dict:
        return dict_to_flat(self.to_json())

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def is_empty(self):
        return not bool(self.raw_data)


class BaseData(metaclass=ABCMeta):
    """
    Abstract Data Model for others Data Models
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_table(self):
        return [self.to_csv()]

    def to_csv(self):
        return dict_to_flat(self.to_json())

    def to_json(self):
        return self.raw_data


class CustomIndicator(BaseModel):
    def __init__(self, raw_data, value=None, severity=None, **kwargs):
        super().__init__(raw_data)
        self.value = value
        self.severity = severity

    def to_csv(self):
        return {
            "Action": self.raw_data.get("action"),
            "Severity": self.raw_data.get("severity"),
            "Signed": self.raw_data.get("metadata", {}).get("signed"),
            "AV Hist": self.raw_data.get("metadata", {}).get("av_hits"),
            "Platforms": convert_list_to_comma_string(
                self.raw_data.get("platforms", [])
            ),
            "Tags": convert_list_to_comma_string(self.raw_data.get("tags", [])),
            "Created At": self.raw_data.get("created_on"),
            "Created By": self.raw_data.get("created_by"),
        }


class ThreatGraphDevice:
    def __init__(self, raw_data, device_id=None, path=None):
        self.raw_data = raw_data
        self.device_id = device_id
        self.path = path


class Process(BaseModel):
    def __init__(
        self,
        raw_data=None,
        device_id=None,
        process_id=None,
        file_name=None,
        command_line=None,
        hostname=None,
        start_timestamp=None,
        stop_timestamp=None,
        indicator_value=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.process_id = process_id
        self.device_id = device_id
        self.file_name = file_name
        self.command_line = command_line
        self.start_timestamp = start_timestamp
        self.stop_timestamp = stop_timestamp
        self.process_name = file_name.split("\\")[-1]
        self.hostname = hostname
        self.indicator_value = indicator_value

    def to_csv(self):
        return {
            "Process ID": self.process_id,
            "Device ID": self.device_id,
            "Process Name": self.process_name,
            "File Name": self.file_name,
            "Command Line": self.command_line,
            "Start Timestamp": self.start_timestamp,
            "Stop Timestamp": self.stop_timestamp,
            "Indicator": self.indicator_value,
        }


class Device(BaseModel):
    def __init__(
        self,
        raw_data,
        cid=None,
        device_id=None,
        bios_manufacturer=None,
        bios_version=None,
        external_ip=None,
        local_ip=None,
        hostname=None,
        mac_address=None,
        machine_domain=None,
        os_version=None,
        last_seen=None,
        platform_name=None,
        system_manufacturer=None,
        system_product_name=None,
        status=None,
        device_policies=None,
        product_type_desc=None,
        agent_version=None,
        online_state=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.cid = cid
        self.device_id = device_id
        self.bios_manufacturer = bios_manufacturer
        self.bios_version = bios_version
        self.external_ip = external_ip
        self.local_ip = local_ip
        self.hostname = hostname
        self.mac_address = mac_address
        self.machine_domain = machine_domain
        self.os_version = os_version
        self.platform_name = platform_name
        self.system_manufacturer = system_manufacturer
        self.system_product_name = system_product_name
        self.status = status
        self.last_seen = last_seen
        self.last_seen_unix = convert_string_to_unix_time(last_seen) if last_seen else 0
        self.product_type_desc = product_type_desc
        self.agent_version = agent_version
        self.online_state = online_state
        self.device_policies = (
            ", ".join(
                [
                    key
                    for key in device_policies.keys()
                    if device_policies[key].get("applied")
                ]
            )
            if device_policies
            else None
        )

    def match_status(self, status):
        return self.status.lower() == status.lower()

    def to_csv(self):
        return {
            "CID": self.cid,
            "Device ID": self.device_id,
            "BIOS Manufacturer": self.bios_manufacturer,
            "BIOD Version": self.bios_version,
            "External IP": self.external_ip,
            "Local IP": self.local_ip,
            "Hostname": self.hostname,
            "Mac Address": self.mac_address,
            "Domain": self.machine_domain,
            "OS Version": self.os_version,
            "Platform Name": self.platform_name,
            "System Manufacturer": self.system_manufacturer,
            "System Product Name": self.system_product_name,
            "Status": self.status,
        }

    def to_enrichment_data(self, exclude_keys=None, additional_prefix=None):
        exclude_keys = exclude_keys or []
        temp_device_data = deepcopy(self.raw_data)

        for key_to_exclude in exclude_keys:
            if key_to_exclude in temp_device_data.keys():
                del temp_device_data[key_to_exclude]

        enrichment_data = dict_to_flat(temp_device_data)
        enrichment_data = add_prefix_to_dict(
            enrichment_data,
            (
                f"{ENRICHMENT_PREFIX}_{additional_prefix}"
                if additional_prefix
                else ENRICHMENT_PREFIX
            ),
        )
        return enrichment_data

    def to_insight(self, entity_type):
        status_color_mapper = {
            "normal": "#339966",
            "contained": "#ff0000",
            "containment_pending": "#ff9900",
            "lift_containment_pending": "#ffcc00",
        }

        status_name_mapper = {
            "normal": "Normal",
            "contained": "Contained",
            "containment_pending": "Pending Containment",
            "lift_containment_pending": "Pending Containment Lift",
        }

        insight_content = "<h2><strong>Status: "
        insight_content += (
            f'</strong><span style="color: {status_color_mapper[self.status.lower()]}">'
            f"{status_name_mapper[self.status]}</span></h2><br/>"
        )
        insight_content += "<p><strong><span>Endpoint Type: "
        insight_content += f"</span></strong><span>{self.product_type_desc}<br />"
        insight_content += f"<strong>OS: </strong>{self.os_version}<br /> "
        insight_content += (
            f"<strong>{INSIGHT_KEYS[entity_type]}: "
            f"</strong>{getattr(self, INSIGHT_VALUES[entity_type])}<br />"
        )
        insight_content += f"<strong>Agent Version: </strong>{self.agent_version}<br />"
        insight_content += f"<strong>Applied policies: </strong>{self.device_policies}"

        return insight_content


class VertexDetails:
    def __init__(self, raw_data):
        self.raw_data = raw_data


class Detection(BaseModel):
    def __init__(
        self,
        raw_data: dict,
        event_type: Optional[str] = None,
        offset: Optional[int] = None,
        event_creation_time: Optional[int] = None,
        severity: Optional[int] = None,
        detect_id: Optional[str] = None,
        detect_name: Optional[str] = None,
        detect_description: Optional[str] = None,
        operation_name: Optional[str] = None,
        service_name: Optional[str] = None,
        session_id: Optional[str] = None,
        audit_information: Optional[dict] = None,
    ):
        super().__init__(raw_data)
        self.event_type = event_type
        self.offset = offset
        self.event_creation_time = event_creation_time
        self.severity = severity if severity else DEFAULT_SEVERITY
        self.detect_id = detect_id
        self.detect_name = detect_name
        self.detect_description = detect_description
        self.operation_name = operation_name
        self.service_name = service_name
        self.session_id = session_id
        self.audit_information = audit_information

    def get_alert_info(
        self,
        environment_common: EnvironmentHandleForDBSystem,
        alert_name_template: Optional[str] = None,
        rule_generator_template: Optional[str] = None,
    ) -> AlertInfo:
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(self.to_flat())

        alert_info.ticket_id = (
            f"{DEFAULT_DEVICE_VENDOR} {self.offset}-{self.event_creation_time}"
        )
        alert_info.display_id = f"{DEFAULT_DEVICE_VENDOR} {self.offset}-{uuid.uuid4()}"
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = f"{DEFAULT_DEVICE_VENDOR} {DEFAULT_DEVICE_PRODUCT}"
        alert_info.name = self.get_field_value(
            self.to_flat(),
            self.default_alert_name,
            alert_name_template,
            CHARACTERS_LIMIT,
        )
        alert_info.description = self.service_name
        alert_info.priority = self.priority
        alert_info.rule_generator = self.get_field_value(
            self.to_flat(),
            self.default_rule_generator_value,
            rule_generator_template,
            CHARACTERS_LIMIT,
        )
        alert_info.end_time = alert_info.start_time = self.event_creation_time
        alert_info.events = [self.to_flat()]

        if self.is_detection:
            alert_info.display_id = alert_info.ticket_id = self.detect_id
            alert_info.description = self.detect_description
        elif self.is_remote_response_session:
            alert_info.description = (
                f"{DEFAULT_DEVICE_VENDOR} Remote session {self.session_id}"
            )
        # update user_activity_audit specific data
        # elif self.is_auth_activity_audit:
        #     pass
        # elif self.is_user_activity_audit:
        #     pass

        return alert_info

    @staticmethod
    def get_field_value(
        data: dict,
        default_value: Optional[str],
        template: Optional[str] = None,
        characters_limit: Optional[int] = None,
    ) -> Optional[str]:
        """
        Formats the given template and cuts value by characters limit

        Args:
            data: Dictionary with placeholder values
            default_value: If there is no given template, returns the default value
            template: String with square brackets (placeholders)
            characters_limit: Maximum amount of char in the returning string

        Returns:
            Formatted string template
        """
        value = format_template(template, data) if template else default_value
        return (
            value[:characters_limit] if characters_limit else value
        ) or default_value

    @property
    def type(self) -> str:
        if self.is_detection:
            return SIEM_DETECTION_EVENT_TYPE
        if self.is_auth_activity_audit:
            return SIEM_AUTH_ACTIVITY_AUDIT_EVENT_TYPE
        if self.is_user_activity_audit:
            return SIEM_USER_ACTIVITY_AUDIT_EVENT_TYPE
        if self.is_remote_response_session:
            return SIEM_REMOTE_RESPONSE_SESSION_EVENT_TYPE
        return SIEM_UNKNOWN_EVENT_TYPE

    @property
    def default_alert_name(self) -> str:
        if self.is_detection:
            return f"{self.detect_name} {self.offset}"
        if self.is_remote_response_session:
            return f"{DEFAULT_DEVICE_VENDOR} {self.offset}-{self.event_type}"
        return f"{DEFAULT_DEVICE_VENDOR} {self.offset}-{self.operation_name}"

    @property
    def default_rule_generator_value(self) -> Optional[str]:
        return self.event_type

    @property
    def is_detection(self) -> bool:
        return bool(self.event_type and self.event_type == DETECTION_EVENT_TYPE)

    @property
    def is_auth_activity_audit(self) -> bool:
        return bool(
            self.event_type and self.event_type == AUTH_ACTIVITY_AUDIT_EVENT_TYPE
        )

    @property
    def is_user_activity_audit(self) -> bool:
        return bool(
            self.event_type and self.event_type == USER_ACTIVITY_AUDIT_EVENT_TYPE
        )

    @property
    def is_remote_response_session(self) -> bool:
        return bool(
            self.event_type
            and self.event_type
            in [
                REMOTE_RESPONSE_SESSION_START_EVENT_TYPE,
                REMOTE_RESPONSE_SESSION_END_EVENT_TYPE,
            ]
        )

    @property
    def priority(self) -> int:
        return CROWD_STRIKE_TO_SIEM_PRIORITIES.get(self.severity, -1)

    @property
    def is_stream_operation(self) -> bool:
        return self.operation_name in {STREAM_STARTED, STREAM_STOPPED}

    def has_creation_time_newer_than(self, min_event_creation_time: int) -> bool:
        """
        Check if creation time of the event is newer than minimum event creation time
        @param min_event_creation_time: Minimum timestamp of the event
        @return: If event.creation_time > min_event_creation_time
        """
        return bool(
            self.event_creation_time
            and self.event_creation_time > min_event_creation_time
        )

    def is_api_stream_action(self, client_id: str, app_prefix: str) -> bool:
        return all(
            [
                self.is_auth_activity_audit,
                self.is_stream_operation,
                self.is_requested_by(client_id),
                self.is_stream_app(app_prefix),
            ]
        )

    def is_requested_by(self, client_id: str) -> bool:
        return client_id == self.audit_information.get(API_CLIENT_ID_KEY)

    def is_stream_app(self, app_prefix: str) -> bool:
        return (
            self.audit_information.get(APP_ID_KEY, "")
            .lower()
            .startswith(app_prefix.lower())
        )


class Stream(BaseData):
    def __init__(self, raw_data, url=None, token=None):
        super(Stream, self).__init__(raw_data)
        self.url = url
        self.token = token

    def to_enrichment_data(self):
        pass


class Behaviors(BaseData):
    def __init__(self, raw_data, scenario="", severity=-1):
        super(Behaviors, self).__init__(raw_data)
        self.scenario = scenario
        self.severity = severity

    def to_enrichment_data(self):
        pass


class DetectionDetail(BaseData):
    def __init__(
        self,
        raw_data,
        first_behavior=None,
        last_behavior=None,
        detection_id=None,
        max_severity=-1,
        behaviors=None,
        max_severity_name="Info",
    ):
        super(DetectionDetail, self).__init__(raw_data)
        self.first_behavior = first_behavior
        self.last_behavior = last_behavior
        self.first_behavior_timestamp = convert_string_to_unix_time(self.first_behavior)
        self.detection_id = detection_id
        self.behaviors = behaviors or []
        self.max_severity = max_severity
        self.max_severity_name = max_severity_name
        self.severity = self.get_severity()
        self.alert_name = self.get_alert_name()

    def get_alert_name(self):
        return (
            self.behaviors[0].scenario.replace("_", " ")
            if self.behaviors
            else DEFAULT_ALERT_NAME
        )

    def get_severity(self):
        # Low
        if self.max_severity_name == "Low":
            return 40
        # Medium
        elif self.max_severity_name == "Medium":
            return 60
        # High
        elif self.max_severity_name == "High":
            return 80
        # Critical
        elif self.max_severity_name == "Critical":
            return 100

        # Informative
        return -1

    def to_events(self, case_name_template: str = "") -> list[SingleJson] | SingleJson:
        if not self.behaviors:
            return dict_to_flat(self.to_json())
        return [
            dict_to_flat(
                self.add_to_event(
                    behavior.to_json(), case_name_template=case_name_template
                )
            )
            for behavior in self.behaviors
        ]

    def add_to_event(
        self,
        event_json: SingleJson,
        case_name_template: str = "",
    ) -> SingleJson:
        """
        Adds behavior data to the event JSON and optionally adds the custom case name.

        Args:
            event_json(SingleJson): The JSON data representing a behavior event.
            case_name_template( str ): An template string for formatting the case name.
            If provided, the case name will be generated using this template and
            the data from the event.

        Returns:
            SingleJson: Events data.
        """
        result_json = deepcopy(self.to_json())
        result_json["behaviors"] = event_json
        if case_name_template:
            result_json["custom_case_name"] = format_template(
                case_name_template,
                result_json,
            )

        return result_json


class AlertDetails(BaseData):
    def __init__(
        self,
        raw_data: dict[str, Any],
        alert_id: str,
        composite_id: str,
        display_name: str,
        description: str,
        product: str,
        severity: int,
        type_: str,
        start_time: str,
        end_time: str,
        created_timestamp: str,
        updated_timestamp: str,
    ):
        super(AlertDetails, self).__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.alert_id = alert_id
        self.composite_id = composite_id
        self.display_name = display_name
        if not self.display_name and type_ == "ods":
            self.display_name = (
                f"On-Demand Scan: {raw_data.get('tactic')} - {raw_data.get('filename')}"
            )
        self.description = description
        self.product = product
        self.severity = severity
        self.type = type_
        self.start_time = (
            convert_string_to_unix_time(start_time) if start_time is not None else None
        )
        self.end_time = (
            convert_string_to_unix_time(end_time) if end_time is not None else None
        )
        self.created_timestamp = convert_string_to_unix_time(created_timestamp)
        self.updated_timestamp = convert_string_to_unix_time(updated_timestamp)
        self.events = []
        self.comments: list[AlertComment] = []

    def get_alert_info(
        self,
        alert_info: AlertInfo,
        environment_common: EnvironmentHandle,
        display_id_prefix: str,
        device_vendor: str,
        device_product: str,
        rule_generator: str,
        alert_name_template: str = "",
        fallback_severity: str | None = None,
    ) -> AlertInfo:
        """Build AlertInfo object.

        Args:
            alert_info: AlertInfo object
            environment_common: environment common for fetching the environment
            display_id_prefix: Display ID prefix
            device_vendor: Device Vendor
            device_product: Device Product
            rule_generator: Rule generator
            alert_name_template: Alert name template.
            fallback_severity: Fallback severity

        Returns:
            (AlertInfo): AlertInfo object
        """
        alert_name = (
            format_template(alert_name_template, self.flat_raw_data)
            if alert_name_template
            else ""
        )
        alert_info.environment = environment_common.get_environment(self.flat_raw_data)
        alert_info.ticket_id = self.composite_id
        alert_info.display_id = f"{display_id_prefix}{self.alert_id}"
        alert_info.name = self.display_name if not alert_name else alert_name
        alert_info.description = self.description
        alert_info.device_vendor = device_vendor
        alert_info.device_product = device_product
        alert_info.priority = self.get_siemplify_severity(fallback_severity)
        alert_info.extensions = {
            "RiskScore": (
                self.severity or ALERTS_CONNECTOR_SEVERITY_MAPPING[fallback_severity]
            ),
            "Severity": self.get_severity_from_value(alert_info.priority),
        }
        alert_info.rule_generator = rule_generator
        alert_info.source_grouping_identifier = self.type
        alert_info.start_time = self.start_time or self.updated_timestamp
        alert_info.end_time = self.end_time or self.updated_timestamp
        alert_info.events = self.to_events()

        return alert_info

    def set_events(self, case_name_template: str = "") -> None:
        """Set alert events

        Args:
            case_name_template: Case name template.
        """
        event_details = deepcopy(self.raw_data)
        if case_name_template:
            event_details["custom_case_name"] = format_template(
                case_name_template,
                event_details,
            )
        self.events.append(event_details)

    def to_events(self):
        """
        Convert alert events to siemplify events
        Args:

        Returns:
           (list): list of flat events
        """
        return [dict_to_flat(event) for event in self.events]

    def get_severity_from_value(self, value: int) -> str:
        """
        Return severity key in camel case (e.g., 'Info', 'Low')
        for a given numeric value.
        """
        for key, val in SEVERITY_MAP.items():
            if val == value:
                return key.capitalize().title()
        return INFO_SEVERITY_NAME

    def get_siemplify_severity(
        self,
        fallback_severity: str | None = None,
    ) -> int:
        """
        Get siemplify severity from alert severity
        Args:
            fallback_severity(str | None): Fallback severity.

        Returns:
            (int): siemplify severity
        """
        if self.severity is None and fallback_severity is not None:
            self.severity = ALERTS_CONNECTOR_SEVERITY_MAPPING[fallback_severity]

        if 0 <= self.severity < ALERTS_CONNECTOR_SEVERITY_MAPPING["low"]:
            return SEVERITY_MAP["INFO"]

        if (
            ALERTS_CONNECTOR_SEVERITY_MAPPING["low"]
            <= self.severity
            < ALERTS_CONNECTOR_SEVERITY_MAPPING["medium"]
        ):
            return SEVERITY_MAP["LOW"]

        if (
            ALERTS_CONNECTOR_SEVERITY_MAPPING["medium"]
            <= self.severity
            < ALERTS_CONNECTOR_SEVERITY_MAPPING["high"]
        ):
            return SEVERITY_MAP["MEDIUM"]

        if (
            ALERTS_CONNECTOR_SEVERITY_MAPPING["high"]
            <= self.severity
            < ALERTS_CONNECTOR_SEVERITY_MAPPING["critical"]
        ):
            return SEVERITY_MAP["HIGH"]

        if ALERTS_CONNECTOR_SEVERITY_MAPPING["high"] <= self.severity <= 100:
            return SEVERITY_MAP["CRITICAL"]

        return SEVERITY_MAP["INFO"]

    def add_comments(self, comments: list[AlertComment]):
        self.comments.extend(comments)


class AlertComment(BaseModel):
    def __init__(
        self,
        raw_data: SingleJson,
        comment: str,
        created_time: str,
    ) -> None:
        super().__init__(raw_data)
        self.comment = comment
        self.created_time = created_time

    @classmethod
    def from_json(cls, comment_data: SingleJson) -> "AlertComment":
        return cls(
            raw_data=comment_data,
            comment=comment_data.get("value"),
            created_time=comment_data.get("timestamp"),
        )


class BehaviorDetails:
    def __init__(self, raw_data):
        self.raw_data = raw_data


class IncidentDetails(BaseAlert):
    def __init__(
        self,
        raw_data: dict,
        incident_type: int,
        incident_id: str,
        first_hostname: str,
        severity: int,
        first_tactics: str,
        start_time: str,
        end_time: str,
    ):
        super(IncidentDetails, self).__init__(raw_data, incident_id)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.incident_type = str(incident_type)
        self.incident_id = incident_id
        self.first_hostname = first_hostname
        self.first_tactics = first_tactics
        self.severity = severity
        self.start_time = convert_string_to_unix_time(start_time)
        self.end_time = convert_string_to_unix_time(end_time)
        self.behavior_ids = []
        self.events = []

    def get_alert_info(
        self, alert_info: AlertInfo, environment_common: EnvironmentHandle
    ) -> AlertInfo:
        """Builds AlertInfo object

        Args:
            alert_info: AlertInfo object
            environment_common: environment common for fetching the environment

        Returns:
            AlertInfo object
        """
        alert_info.environment = environment_common.get_environment(self.flat_raw_data)
        alert_info.ticket_id = self.incident_id
        alert_info.display_id = f"{INCIDENTS_CONNECTOR_ALERT_DISPLAY_ID_PREFIX}_{self.incident_id}_{len(self.behavior_ids)}"
        alert_info.name = (
            f"{INCIDENTS_CONNECTOR_ALERT_DISPLAY_NAME_PREFIX}: {self.first_hostname}"
        )
        alert_info.device_vendor = INCIDENTS_CONNECTOR_DEVICE_VENDOR
        alert_info.device_product = INCIDENTS_CONNECTOR_DEVICE_PRODUCT
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = (
            f"{INCIDENTS_CONNECTOR_RULE_GENERATOR_PREFIX}: {self.first_tactics}"
        )
        alert_info.source_grouping_identifier = self.incident_id
        alert_info.start_time = self.start_time
        alert_info.end_time = self.end_time
        alert_info.events = self.to_events()

        return alert_info

    def set_events(self, behaviors: list):
        """Set alert events

        Args:
            behaviors: List of behaviors details
        """
        incident_event = [deepcopy(self.raw_data)]
        behavior_events = [deepcopy(behavior.raw_data) for behavior in behaviors]
        self.events = incident_event + behavior_events

    def to_events(self) -> list:
        """Convert alert events to siemplify events

        Returns:
           List of flat events
        """
        return [dict_to_flat(event) for event in self.events]

    def get_siemplify_severity(self) -> int:
        """Get Siemplify severity from alert severity

        Returns:
            Siemplify severity
        """
        low = INCIDENTS_CONNECTOR_SEVERITY_MAPPING["low"]
        medium = INCIDENTS_CONNECTOR_SEVERITY_MAPPING["medium"]
        high = INCIDENTS_CONNECTOR_SEVERITY_MAPPING["high"]
        critical = INCIDENTS_CONNECTOR_SEVERITY_MAPPING["critical"]

        if self.severity >= critical:
            return SEVERITY_MAP["CRITICAL"]
        elif self.severity >= high:
            return SEVERITY_MAP["HIGH"]
        elif self.severity >= medium:
            return SEVERITY_MAP["MEDIUM"]
        elif self.severity >= low:
            return SEVERITY_MAP["LOW"]

        return SEVERITY_MAP["INFO"]


class Command(BaseModel):
    def __init__(self, raw_data, complete=None, **kwargs):
        super().__init__(raw_data)
        self.complete = complete


class VulnerabilityList:
    def __init__(self, vulnerabilities, remediations, total):
        self.vulnerabilities = vulnerabilities
        self.remediations = remediations
        self.total = total

    def add_vulnerabilities(self, vulnerabilities):
        self.vulnerabilities.extend(vulnerabilities)

    def to_json(self):
        json_data = {
            "statistics": {
                "total": self.total,
                "severity": {
                    "critical": self.count_of_severities(
                        severity=Severity.CRITICAL.value
                    ),
                    "high": self.count_of_severities(severity=Severity.HIGH.value),
                    "medium": self.count_of_severities(severity=Severity.MEDIUM.value),
                    "low": self.count_of_severities(severity=Severity.LOW.value),
                    "unknown": self.count_of_severities(
                        severity=Severity.UNKNOWN.value
                    ),
                },
                "status": {
                    "open": self.count_of_status(status=OPEN),
                    "reopened": self.count_of_status(status=REOPEN),
                },
                "total_available_remediations": self.total_available_remediations(),
            },
            "details": [
                vulnerability.to_json_with_remediation_details(self.remediations)
                for vulnerability in self.vulnerabilities
            ],
        }

        return json_data

    def total_available_remediations(self):
        vulnerability_unique_ids = set(
            [
                vulnerability.ids[0] if len(vulnerability.ids) > 0 else ""
                for vulnerability in self.vulnerabilities
            ]
        )
        return sum(
            [
                1 if vulnerability_id else 0
                for vulnerability_id in vulnerability_unique_ids
            ]
        )

    def count_of_severities(self, severity):
        return sum(
            [
                1 if vulnerability.severity == severity else 0
                for vulnerability in self.vulnerabilities
            ]
        )

    def count_of_status(self, status):
        return sum(
            [
                1 if vulnerability.status == status else 0
                for vulnerability in self.vulnerabilities
            ]
        )

    def to_insight(self):
        return (
            f"<h2><strong>TOTAL: {self.total}</strong></h2><br><p><strong>Critical: {self.count_of_severities(severity='CRITICAL')}"
            f"<br /></strong><strong>High:&nbsp;{self.count_of_severities(severity='HIGH')}"
            f"<br />Medium:&nbsp;{self.count_of_severities(severity='MEDIUM')}"
            f"<br />Low:&nbsp;{self.count_of_severities(severity='LOW')}"
            f"<br />Unknown:&nbsp;{self.count_of_severities(severity='UNKNOWN')}</strong></p>"
        )


class VulnerabilityDetail(BaseData):
    def __init__(
        self,
        raw_data,
        id=None,
        cid=None,
        aid=None,
        created_timestamp=None,
        updated_timestamp=None,
        status=None,
        cve=None,
        app=None,
        apps=None,
        host_info=None,
        severity=None,
        ids=None,
        cve_id=None,
        score=None,
        product_name_version=None,
        **kwargs,
    ):
        super().__init__(raw_data)
        self.id = id
        self.cid = cid
        self.aid = aid
        self.created_timestamp = created_timestamp
        self.updated_timestamp = updated_timestamp
        self.status = status
        self.cve = cve
        self.app = app or {}
        self.apps = apps or []
        self.product_name_version = product_name_version
        self.severity = severity
        self.host_info = host_info
        self.ids = ids or []
        self.score = score
        self.cve_id = cve_id

    def to_csv(self):
        return {
            "Name": self.cve_id,
            "Score": self.score,
            "Severity": self.severity,
            "Status": self.status,
            "App": self.product_name_version,
            "Has Remediation": bool(self.ids),
        }

    def to_json_with_remediation_details(self, remediation_details):
        result_json = self.to_json().copy()
        result_json["remediation"] = [
            remediation.to_json()
            for remediation in remediation_details
            if remediation.id in self.ids
        ]
        return result_json


class RemediationDetail(BaseData):
    def __init__(self, raw_data, resources=None, id=None, **kwargs):
        super().__init__(raw_data)
        self.resources = resources or []
        self.id = id


class BatchSession(BaseModel):
    def __init__(self, raw_data, batch_id, device_id):
        super().__init__(raw_data)
        self.batch_id = batch_id
        self.session_id = raw_data.get(device_id).get("session_id")
        self.completed = raw_data.get(device_id).get("complete")


class BatchCommand(BaseModel):
    def __init__(self, raw_data, sha256, session_id, name, cloud_request_id, **kwargs):
        super().__init__(raw_data)
        self.sha256 = sha256
        self.session_id = session_id
        self.name = name
        self.cloud_request_id = cloud_request_id


class HostGroup(BaseModel):
    def __init__(self, raw_data, id, name):
        super(HostGroup, self).__init__(raw_data)
        self.id = id
        self.name = name


class LoginHistory(BaseModel):
    def __init__(self, raw_data, device_id, recent_logins):
        super().__init__(raw_data)
        self.device_id = device_id
        self.recent_logins = recent_logins


class OnlineState(BaseModel):
    def __init__(self, raw_data, device_id, state):
        super().__init__(raw_data)
        self.device_id = device_id
        self.state = state


class SubmissionData(BaseModel):
    def __init__(self, raw_data, _id, state):
        super().__init__(raw_data=raw_data)
        self.id = _id
        self.state = state

    def get_entity_name(self):
        return self.raw_data["sandbox"][0]["submit_name"]


class SubmissionReport(BaseModel):
    def __init__(self, raw_data, _id):
        super().__init__(raw_data=raw_data)
        self.id = _id

    def get_entity_name(self):
        return self.raw_data["sandbox"][0]["submit_name"]


class File(BaseModel):
    def __init__(self, raw_data, name, sha256):
        super().__init__(raw_data=raw_data)
        self.name = name
        self.sha256 = sha256


class IncidentData(BaseModel):
    """
    Class to create data model for Incident data
    """

    def __init__(self, raw_data: dict, message: str) -> None:
        super().__init__(raw_data)
        self.message = message


class OnDemandScanData(BaseModel):
    """Data model for On Demand Scan data."""

    def __init__(
        self,
        raw_data: SingleJson,
        resources: SingleJson,
        scan_id: str,
        status: str,
        hosts: list[str] | None = None,
        host_groups: list[str] | None = None,
        file_paths: list[str] | None = None,
        scan_exclusions: list[str] | None = None,
        cpu_priority: str | None = None,
        cloud_ml_detection_level: str | None = None,
        cloud_ml_prevention_level: str | None = None,
        sensor_ml_detection_level: str | None = None,
        sensor_ml_prevention_level: str | None = None,
        created_on: str | None = None,
        updated_on: str | None = None,
        description: str | None = None,
        endpoint_notification: bool | None = None,
        quarantine: bool | None = False,
        max_duration: int | None = None,
        cid: str | None = None,
    ) -> None:
        super().__init__(raw_data)
        self.resources = resources
        self.scan_id = scan_id
        self.status = status
        self.hosts = hosts
        self.host_groups = host_groups
        self.file_paths = file_paths
        self.scan_exclusions = scan_exclusions
        self.cpu_priority = cpu_priority
        self.cloud_ml_detection_level = cloud_ml_detection_level
        self.cloud_ml_prevention_level = cloud_ml_prevention_level
        self.sensor_ml_detection_level = sensor_ml_detection_level
        self.sensor_ml_prevention_level = sensor_ml_prevention_level
        self.created_on = created_on
        self.updated_on = updated_on
        self.description = description
        self.endpoint_notification = endpoint_notification
        self.quarantine = quarantine
        self.max_duration = max_duration
        self.cid = cid


@dataclasses.dataclass
class SearchEventsData:
    job_id: str
    cancelled: bool
    done: bool
    events: list[SingleJson]

    @classmethod
    def from_json(cls, raw_json: str, job_id: str) -> "SearchEventsData":
        return cls(
            job_id=job_id,
            cancelled=raw_json.get("cancelled", False),
            done=raw_json.get("done", False),
            events=raw_json.get("events", []),
        )

    @property
    def status(self) -> str:
        """Job status."""
        if not self.cancelled and not self.done:
            return EventStatus.IN_PROGRESS.value

        if self.cancelled:
            return EventStatus.CANCELLED.value

        return EventStatus.COMPLETED.value
