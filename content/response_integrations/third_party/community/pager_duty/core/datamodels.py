from __future__ import annotations

from typing import Any

from SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time, dict_to_flat
from TIPCommon.data_models import BaseAlert

from .constants import INTEGRATION_NAME, PAGERDUTY_SEVERITY_MAPPING


class PagerDutyIncident(BaseAlert):
    def __init__(self, raw_data: dict[str, Any], alert_id: str):
        super().__init__(raw_data, alert_id)
        self.created_at = raw_data.get("created_at")

    def get_priority(self) -> int:
        urgency = self.raw_data.get("urgency", "low").lower()
        return PAGERDUTY_SEVERITY_MAPPING.get(urgency, 40)

    def get_severity_label(self, priority: int) -> str:
        if priority == 80:
            return "HIGH"
        if priority == 40:
            return "LOW"
        return "INFORMATIONAL"

    def get_alert_info(self, env_common: Any) -> AlertInfo:
        alert_info = AlertInfo()
        incident = self.raw_data
        
        alert_info.display_id = incident["id"]
        alert_info.ticket_id = incident["id"]
        alert_info.name = incident['id']
        alert_info.rule_generator = (
            incident.get("first_trigger_log_entry", {}).get("summary", "No Summary")
        )
        alert_info.start_time = convert_string_to_unix_time(incident["created_at"])
        alert_info.end_time = alert_info.start_time
        
        alert_info.priority = self.get_priority()
        alert_info.severity = self.get_severity_label(alert_info.priority)
        
        alert_info.device_vendor = INTEGRATION_NAME
        alert_info.device_product = INTEGRATION_NAME
        alert_info.environment = env_common.get_environment(dict_to_flat(incident))
        alert_info.events.append(dict_to_flat(incident))
        
        return alert_info
