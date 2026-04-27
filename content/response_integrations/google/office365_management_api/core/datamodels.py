from __future__ import annotations
import copy
import json
import uuid
from .constants import (
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    SEVERITY_MAP,
    AUDIT_GENERAL_SEVERITY_MAP,
)
from TIPCommon import dict_to_flat
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from .UtilsManager import mask_string


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data


class DataBlob(BaseModel):
    def __init__(self, raw_data, url):
        super(DataBlob, self).__init__(raw_data)
        self.url = url


class Alert(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        workload,
        operation,
        policy_names,
        incident_id,
        creation_time,
        policy_details,
        mask_findings,
    ):
        super(Alert, self).__init__(raw_data)
        self.id = id
        self.uuid = uuid.uuid4()
        self.workload = workload
        self.operation = operation
        self.policy_names = policy_names
        self.incident_id = incident_id
        self.creation_time = convert_string_to_unix_time(f"{creation_time}Z")
        self.policy_details = policy_details
        self.mask_findings = mask_findings

    def get_alert_info(self, alert_info, environment_common):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = f"{self.workload} {self.operation}"
        alert_info.description = f"{self.workload} {self.operation}"
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = f"{self.workload} {self.operation}"
        alert_info.source_grouping_identifier = self.incident_id
        alert_info.start_time = self.creation_time
        alert_info.end_time = self.creation_time
        alert_info.events = self.create_events()

        return alert_info

    def create_events(self):
        events = []

        for policy_detail in self.policy_details:
            if self.mask_findings:
                self.mask_sensitive_data(policy_detail)

            self.raw_data["PolicyDetails"] = policy_detail
            events.append(dict_to_flat(self.raw_data))

        return events

    def get_siemplify_severity(self):
        severities = []

        for policy_detail in self.policy_details:
            severities.extend(
                [
                    SEVERITY_MAP.get(rule.get("Severity"), 40)
                    for rule in policy_detail.get("Rules", [])
                ]
            )

        return max(severities)

    def mask_sensitive_data(self, policy_details):
        rules = policy_details.get("Rules")

        for rule in rules:
            sensitive_data = rule.get("ConditionsMatched", {}).get(
                "SensitiveInformation", []
            )

            for data in sensitive_data:
                detected_values = data.get("SensitiveInformationDetections", {}).get(
                    "DetectedValues", []
                )

                for detected_value in detected_values:
                    detected_value["Name"] = (
                        mask_string(detected_value.get("Name"))
                        if detected_value.get("Name")
                        else ""
                    )
                    detected_value["Value"] = (
                        mask_string(detected_value.get("Value"))
                        if detected_value.get("Value")
                        else ""
                    )


class AuditGeneralAlert(BaseModel):
    def __init__(
        self,
        raw_data,
        id,
        workload,
        operation,
        incident_id,
        creation_time,
        severity,
        status,
    ):
        super(AuditGeneralAlert, self).__init__(raw_data)
        self.id = id
        self.uuid = uuid.uuid4()
        self.workload = workload
        self.operation = operation
        self.incident_id = incident_id
        self.creation_time = convert_string_to_unix_time(f"{creation_time}Z")
        self.severity = severity
        self.status = status
        self.data = {}
        self.events = []

    def get_alert_info(self, alert_info, environment_common):
        alert_info.environment = environment_common.get_environment(self.raw_data)
        alert_info.ticket_id = self.id
        alert_info.display_id = str(self.uuid)
        alert_info.name = f"{self.workload}, {self.operation}"
        alert_info.description = f"{self.workload}, {self.operation}"
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.device_product = DEVICE_PRODUCT
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = f"{self.workload}, {self.operation}"
        alert_info.source_grouping_identifier = self.incident_id
        alert_info.start_time = self.creation_time
        alert_info.end_time = self.creation_time
        alert_info.events = self.events

        return alert_info

    def set_events(self, entity_events_keys_list, event_field_name):
        event_raw_data = copy.deepcopy(self.raw_data)
        data = event_raw_data.get("Data", {})
        self.data = json.loads(data) if data else {}
        event_raw_data = dict(self.data, **event_raw_data)
        events = [dict_to_flat(event_raw_data)]

        for entity in self.data.get("Entities", []):
            if entity.get("Type") in entity_events_keys_list:
                entity["CreationTime"] = event_raw_data.get("CreationTime")
                entity_id = entity.pop("$id", None)

                if not entity.get(event_field_name):
                    entity[event_field_name] = entity.get("Type")

                if entity_id:
                    entity["id"] = entity_id

                events.append(dict_to_flat(entity))

        self.events = events

    def get_siemplify_severity(self):
        severity = self.severity or self.data.get("Severity")
        return AUDIT_GENERAL_SEVERITY_MAP.get(severity, 40)
