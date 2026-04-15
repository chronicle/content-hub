from __future__ import annotations
from datetime import datetime
from typing import Optional, Union

from EnvironmentCommon import (
    EnvironmentHandleForDBSystem,
    EnvironmentHandleForFileSystem,
)
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_datetime_to_unix_time
from TIPCommon.transformation import dict_to_flat
from ..core.constants import (
    DEFAULT_DEVICE_VENDOR,
    DEFAULT_DEVICE_PRODUCT,
    DEFAULT_RULE_GENERATOR,
    DEFAULT_SOURCE_GROUPING_IDENTIFIER,
)


class BaseModel:
    def __init__(self, raw_data: dict) -> None:
        self.raw_data = raw_data

    def to_json(self) -> dict:
        return self.raw_data

    def to_flat(self) -> dict:
        return dict_to_flat(self.to_json())


class Incident(BaseModel):
    def __init__(
        self,
        raw_data: dict,
        email_subject: Optional[str],
        incident_number: Optional[str],
        report_datetime: str,
    ) -> None:
        super().__init__(raw_data)
        self.email_subject = email_subject
        self.incident_number = incident_number
        self.report_datetime = datetime.strptime(
            report_datetime, "%Y-%m-%d %H:%M:%S.%f"
        )

    def create_alert_info(
        self,
        alert_severity: str,
        environment_common: Union[
            EnvironmentHandleForDBSystem, EnvironmentHandleForFileSystem
        ],
        device_product_field_name: str,
    ) -> AlertInfo:
        """
        Transform Incident object to AlertInfo

        Args:
            alert_severity: Alert's severity. Possible values can be:
                            Informational, Low, Medium, High, Critical
            environment_common: The environment common object for fetching the environment
            device_product_field_name: The device product field name

        Returns:
            AlertInfo object
        """
        alert_info = AlertInfo()
        alert_info.ticket_id = self.incident_number
        alert_info.display_id = f"PhishRod_{self.incident_number}"
        alert_info.name = self.email_subject
        alert_info.reason = None
        alert_info.description = None
        alert_info.device_vendor = DEFAULT_DEVICE_VENDOR
        alert_info.device_product = (
            self.raw_data.get(device_product_field_name) or DEFAULT_DEVICE_PRODUCT
        )
        alert_info.priority = alert_severity
        alert_info.rule_generator = DEFAULT_RULE_GENERATOR
        alert_info.source_grouping_identifier = DEFAULT_SOURCE_GROUPING_IDENTIFIER
        alert_info.start_time = convert_datetime_to_unix_time(self.report_datetime)
        alert_info.end_time = convert_datetime_to_unix_time(self.report_datetime)
        alert_info.environment = environment_common.get_environment(
            dict_to_flat(self.to_json())
        )
        alert_info.events = [self.to_flat()]

        return alert_info


class UpdateIncidentData(BaseModel):
    """
    Class to create data model for Update Incident
    """

    def __init__(self, raw_data: dict, message: str, status_marked: bool) -> None:
        super().__init__(raw_data)
        self.status_marked = status_marked
        self.message = message


class MarkIncidentData(BaseModel):
    """
    Class to create data model for Mark Incident
    """

    def __init__(self, raw_data: dict, status: str, code: str) -> None:
        super().__init__(raw_data)
        self.status = status
        self.code = code
