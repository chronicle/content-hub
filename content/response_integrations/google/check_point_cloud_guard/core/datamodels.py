from __future__ import annotations
from TIPCommon import dict_to_flat
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from . import consts
import uuid


SEVERITIES = {"Informational": -1, "Low": 40, "Medium": 60, "High": 80, "Critical": 100}


class Finding:
    def __init__(
        self,
        raw_data,
        id=None,
        createdTime=None,
        updatedTime=None,
        findingKey=None,
        cloudAccountType=None,
        comments=None,
        alertType=None,
        ruleId=None,
        ruleName=None,
        ruleLogic=None,
        entityName=None,
        entityType=None,
        severity=None,
        description=None,
        origin=None,
        acknowledged=None,
        status=None,
        category=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.created_time = createdTime
        self.updated_time = updatedTime
        self.finding_key = findingKey
        self.cloud_account_type = cloudAccountType
        self.comments = comments
        self.alert_type = alertType
        self.severity = severity
        self.siemplify_severity = SEVERITIES.get(severity, -1)
        self.rule_id = ruleId
        self.rule_name = ruleName
        self.rule_ogic = ruleLogic
        self.entity_name = entityName
        self.entity_type = entityType
        self.description = description
        self.origin = origin
        self.acknowledged = acknowledged
        self.status = status
        self.category = category

        try:
            self.created_time_ms = convert_string_to_unix_time(self.created_time)
        except Exception:
            self.created_time_ms = 1

        try:
            self.updated_time_ms = convert_string_to_unix_time(self.updated_time)
        except Exception:
            self.updated_time_ms = 1

    def as_json(self):
        return self.raw_data

    def as_event(self):
        if self.entity_type:
            self.raw_data[self.entity_type] = self.entity_name
        return dict_to_flat(self.raw_data)

    def as_csv(self):
        return {
            "Finding ID": self.id,
            "Created Time": self.created_time,
            "Updated Time": self.updated_time,
            "Rule Name": self.rule_name,
            "Rule ID": self.rule_id,
            "Description": self.description,
            "Status": self.status,
            "Category": self.category,
            "Entity Name": self.entity_name,
            "Entity Type": self.entity_type,
            "Alert Type": self.alert_type,
            "Severity": self.severity,
        }

    def as_alert_info(self, environment_common):
        """
        Create an AlertInfo out of the current finding
        :param environment_common: {EnvironmentHandle} The environment common object for fetching the environment
        :return: {AlertInfo} The created AlertInfo object
        """
        alert_info = AlertInfo()
        alert_info.environment = environment_common.get_environment(self.as_event())
        alert_info.ticket_id = self.id
        alert_info.display_id = str(uuid.uuid4())
        alert_info.name = self.rule_name
        alert_info.description = self.description
        alert_info.device_vendor = consts.VENDOR
        alert_info.device_product = consts.PRODUCT
        alert_info.priority = self.siemplify_severity
        alert_info.rule_generator = self.alert_type
        alert_info.start_time = self.created_time_ms
        alert_info.end_time = self.created_time_ms
        alert_info.events = [self.as_event()]
        return alert_info
