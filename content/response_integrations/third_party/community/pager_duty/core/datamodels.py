from __future__ import annotations

from typing import Any

from SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time, dict_to_flat
from TIPCommon.data_models import BaseAlert
from TIPCommon.envcommon import EnvironmentHandle

from .constants import (
    HIGH_PRIORITY,
    INTEGRATION_NAME,
    LOW_PRIORITY,
    PAGERDUTY_SEVERITY_MAPPING,
)


class PagerDutyIncident(BaseAlert):
    """Represents a PagerDuty incident alert."""

    def __init__(self, raw_data: dict[str, Any], alert_id: str) -> None:
        """Initialize PagerDutyIncident.

        Args:
            raw_data: Raw incident payload dictionary from PagerDuty.
            alert_id: Identifier for the alert.
        """
        super().__init__(raw_data, alert_id)
        self.created_at = raw_data.get("created_at")

    def get_priority(self) -> int:
        """Get incident priority based on urgency.

        Returns:
            Integer priority value.
        """
        urgency = self.raw_data.get("urgency", "low").lower()
        return PAGERDUTY_SEVERITY_MAPPING.get(urgency, LOW_PRIORITY)

    def get_severity_label(self, priority: int) -> str:
        """Map integer priority value to severity label string.

        Args:
            priority: Priority integer to convert.

        Returns:
            Severity label string (HIGH, LOW, or INFORMATIONAL).
        """
        if priority == HIGH_PRIORITY:
            return "HIGH"
        if priority == LOW_PRIORITY:
            return "LOW"
        return "INFORMATIONAL"

    def get_alert_info(self, env_common: EnvironmentHandle) -> AlertInfo:
        """Build AlertInfo object from incident data.

        Args:
            env_common: EnvironmentHandle for fetching the environment.

        Returns:
            AlertInfo instance configured with incident metadata and events.
        """
        alert_info = AlertInfo()
        incident = self.raw_data

        alert_info.display_id = incident["id"]
        alert_info.ticket_id = incident["id"]
        alert_info.name = incident["id"]
        first_log = incident.get("first_trigger_log_entry", {})
        alert_info.rule_generator = first_log.get("summary", "No Summary")
        alert_info.start_time = convert_string_to_unix_time(
            incident["created_at"]
        )
        alert_info.end_time = alert_info.start_time

        alert_info.priority = self.get_priority()
        alert_info.severity = self.get_severity_label(alert_info.priority)

        alert_info.device_vendor = INTEGRATION_NAME
        alert_info.device_product = INTEGRATION_NAME
        flat_incident = dict_to_flat(incident)
        alert_info.environment = env_common.get_environment(flat_incident)
        alert_info.events.append(flat_incident)

        return alert_info
