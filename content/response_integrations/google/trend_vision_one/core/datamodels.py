from __future__ import annotations

from typing import NamedTuple

import copy
from .constants import (
    INTEGRATION_PREFIX,
    DEVICE_VENDOR,
    DEVICE_PRODUCT,
    SEVERITY_MAPPING,
)
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from EnvironmentCommon import EnvironmentHandle
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
from TIPCommon import dict_to_flat, add_prefix_to_dict, convert_list_to_comma_string


class AgentResult(NamedTuple):
    successful_agents: list[Endpoint]
    failed_agents: list[str]


class BaseModel:
    """
    Base model for inheritance
    """

    def __init__(self, raw_data):
        self.raw_data = raw_data

    def to_json(self):
        return self.raw_data

    def to_table(self):
        return dict_to_flat(self.to_json())

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.raw_data)
        return add_prefix_to_dict(data, prefix) if prefix else data


class Alert(BaseModel):
    def __init__(
        self, raw_data, alert_id, model, description, severity, created_datetime
    ):
        super().__init__(raw_data)
        self.flat_raw_data = dict_to_flat(raw_data)
        self.alert_id = alert_id
        self.model = model
        self.description = description
        self.severity = severity
        self.created_datetime = convert_string_to_unix_time(created_datetime)
        self.events = []

    def get_alert_info(
        self,
        alert_info: AlertInfo,
        environment_common: EnvironmentHandle,
        device_product_field: str,
    ) -> AlertInfo:
        """
        Build AlertInfo object
        Args:
            alert_info (AlertInfo): AlertInfo object
            environment_common (EnvironmentHandle): environment common for fetching the environment
            device_product_field (str): key to use to fetch device product value

        Returns:
            (AlertInfo): AlertInfo object
        """
        alert_info.ticket_id = self.alert_id
        alert_info.display_id = f"{INTEGRATION_PREFIX}_{self.alert_id}"
        alert_info.name = self.model
        alert_info.description = self.description
        alert_info.device_vendor = DEVICE_VENDOR
        alert_info.priority = self.get_siemplify_severity()
        alert_info.rule_generator = self.model
        alert_info.source_grouping_identifier = self.model
        alert_info.start_time = self.created_datetime
        alert_info.end_time = self.created_datetime
        alert_info.events = self.to_events()
        alert_info.environment = environment_common.get_environment(
            alert_info.events[0]
        )
        alert_info.device_product = (
            alert_info.events[0].get(device_product_field) or DEVICE_PRODUCT
        )

        return alert_info

    def get_siemplify_severity(self) -> int:
        """
        Get siemplify severity from alert severity
        Args:

        Returns:
            (int): siemplify severity
        """
        return SEVERITY_MAPPING.get(self.severity.upper(), -1)

    def set_events(self) -> None:
        """
        Set Alert events
        Args:

        Returns:
           (): None
        """
        entities = self.raw_data.get("impactScope", {}).get("entities", [])
        indicators = self.raw_data.get("indicators", [])

        for indicator in indicators:
            indicator[indicator.get("field", "")] = indicator.get("value", "")

        for entity in entities:
            entity[entity.get("entityType", "")] = (
                entity.get("entityValue", {}).get("name", "")
                if isinstance(entity.get("entityValue", {}), dict)
                else entity.get("entityValue", "")
            )

        for i in range(max(len(entities), len(indicators))):
            event_data = copy.deepcopy(self.raw_data)
            event_data.get("impactScope", {})["entities"] = (
                entities[i] if i < len(entities) else {}
            )
            event_data["indicators"] = indicators[i] if i < len(indicators) else {}

            self.events.append(event_data)

    def to_events(self):
        """
        Convert Alert events to siemplify events
        Args:

        Returns:
           (list): list of flat events
        """
        return [dict_to_flat(event) for event in self.events]


class Endpoint(BaseModel):
    def __init__(
        self,
        raw_data,
        guid,
        os_description,
        login_account_value,
        endpoint_name_value,
        ip_value,
        installed_product_codes,
    ):
        super().__init__(raw_data)
        self.guid = guid
        self.os_description = os_description
        self.login_account_value = login_account_value
        self.endpoint_name_value = endpoint_name_value
        self.ip_value = ip_value
        self.installed_product_codes = installed_product_codes

    def to_table(self):
        table_data = {
            "os": self.os_description,
            "login_account": convert_list_to_comma_string(self.login_account_value),
            "endpoint_name": self.endpoint_name_value,
            "ip": convert_list_to_comma_string(self.ip_value),
            "installedProductCodes": convert_list_to_comma_string(
                self.installed_product_codes
            ),
        }
        return {key: value for key, value in table_data.items() if value is not None}

    def to_enrichment_data(self, prefix=None):
        data = dict_to_flat(self.to_table())
        return add_prefix_to_dict(data, prefix) if prefix else data


class Task(BaseModel):
    def __init__(self, raw_data, status, id):
        super(Task, self).__init__(raw_data)
        self.id = id
        self.status = status


class Script(BaseModel):
    pass


class SubmitFile(BaseModel):

    def __init__(self, raw_data, task_id=None):
        super(SubmitFile, self).__init__(raw_data)
        self.id = task_id


class SubmitURL(BaseModel):

    def __init__(self, raw_data, task_id=None, url=None):
        super(SubmitURL, self).__init__(raw_data)
        self.id = task_id
        self.url = url


class ExecuteEmail(BaseModel):

    def __init__(self, raw_data, task_id=None, url=None, error_message=None):
        super(ExecuteEmail, self).__init__(raw_data)
        self.id = task_id
        self.url = url
        self.error_message = error_message


class TaskDetail(BaseModel):

    def __init__(self, raw_data, task_id=None, action=None, status=None):
        super(TaskDetail, self).__init__(raw_data)
        self.id = task_id
        self.action = action
        self.status = status
