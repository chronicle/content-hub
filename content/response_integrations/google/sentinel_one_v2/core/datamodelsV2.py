from __future__ import annotations
import dataclasses
from sentinel_one_v2.core.datamodels import Threat, BaseModel
from TIPCommon.transformation import dict_to_flat
from sentinel_one_v2.core.constants import (
    ALERTS_CONNECTOR_SEVERITY_MAPPING,
    DEFAULT_PRODUCT,
    DEFAULT_VENDOR,
    SEVERITY_MAP,
    THREAT_TRUE_POSITIVE,
)
from sentinel_one_v2.core.utils import transform_template_string
from soar_sdk.SiemplifyConnectorsDataModel import AlertInfo
from soar_sdk.SiemplifyUtils import convert_string_to_unix_time


class ThreatV21(Threat):
    def __init__(
        self,
        incident_status_dsc=None,
        analyst_verdict_dsc=None,
        process_user=None,
        agent_computer_name=None,
        incident_status=None,
        analyst_verdict=None,
        mitigation_statuses=None,
        *args,
        **kwargs,
    ):
        super().__init__(analyst_verdict=analyst_verdict, *args, **kwargs)

        self.incident_status_dsc = incident_status_dsc
        self.analyst_verdict_dsc = analyst_verdict_dsc
        self.process_user = process_user
        self.agent_computer_name = agent_computer_name
        self.incident_status = incident_status
        self.is_true_positive = analyst_verdict == THREAT_TRUE_POSITIVE
        self.mitigation_statuses = mitigation_statuses

    def to_csv(self):
        return {
            "Analyst Verdict": self.analyst_verdict_dsc,
            "Incident Status": self.incident_status_dsc,
            "Name": self.threat_name,
            "Endpoint": self.agent_computer_name,
            "Process User": self.process_user,
        }


class MitigationStatus(BaseModel):
    def __init__(self, raw_data, action=None, status=None):
        super().__init__(raw_data)
        self.action = action
        self.status = status

    def has_action(self, action):
        return self.action.replace("-", "") == action.replace("-", "")


@dataclasses.dataclass(slots=True)
class Alert(BaseModel):
    """Class to create data model for Alert object"""

    raw_data: dict
    raw_flat_data: dict
    alert_id: str
    rule_name: str
    created_at: str
    creation_time_unix_time: int
    severity: str
    description: str | None
    rule_id: str | None
    rule_query: str | None
    incident_status: str | None
    verdict: str | None
    s1ql: str | None

    @classmethod
    def from_json(cls, raw_data: dict) -> "Alert":
        """Create Alert object from raw json data
        Args:
            raw_data (dict): raw data of alert
        Returns:
            Alert: Alert object
        """
        alert_info = raw_data.get("alertInfo", {})
        rule_info = raw_data.get("ruleInfo", {})
        return cls(
            raw_data=raw_data,
            raw_flat_data=dict_to_flat(raw_data),
            alert_id=alert_info.get("alertId"),
            incident_status=alert_info.get("incidentStatus"),
            verdict=alert_info.get("analystVerdict"),
            rule_name=rule_info.get("name"),
            created_at=alert_info.get("createdAt"),
            creation_time_unix_time=convert_string_to_unix_time(
                alert_info.get("createdAt")
            ),
            severity=rule_info.get("severity", ""),
            description=rule_info.get("description"),
            rule_id=rule_info.get("id"),
            rule_query=rule_info.get("s1ql"),
            s1ql=rule_info.get("s1ql"),
        )

    def get_alert_info(
        self,
        alert_name_template: str | None,
        case_name_template: str | None,
        environment_common,
    ) -> AlertInfo:
        """Create a complete AlertInfo object using templates and environment data."""
        alert_info = AlertInfo()
        alert_info.ticket_id = self.alert_id
        alert_info.display_id = f"SentinelOne_Alert_{self.alert_id}"
        alert_info.rule_generator = f"SentinelOne Alert: {self.rule_name}" or "Unknown"

        if alert_name_template:
            alert_info.name = transform_template_string(
                alert_name_template, self.raw_flat_data
            )
        else:
            alert_info.name = alert_info.rule_generator

        alert_info.description = self.description or "No description provided"
        alert_info.device_vendor = DEFAULT_VENDOR
        alert_info.device_product = DEFAULT_PRODUCT
        alert_info.priority = SEVERITY_MAP.get(self.severity.upper())
        alert_info.extensions = {
            "RiskScore": (
                ALERTS_CONNECTOR_SEVERITY_MAPPING.get(self.severity.lower(), -1)
            ),
            "Severity": self.severity
        }
        alert_info.source_grouping_identifier = self.rule_name or "Unknown"
        alert_info.start_time = self.creation_time_unix_time
        alert_info.end_time = self.creation_time_unix_time
        alert_info.environment = environment_common.get_environment(self.raw_flat_data)
        events = self.build_events_data()
        event_dict = events[0]
        event_dict["TicketId"] = self.alert_id
        alert_info.events = events

        if case_name_template:
            case_name = transform_template_string(
                case_name_template, self.raw_flat_data
            )
            if case_name:
                event_dict["custom_case_name"] = case_name

        return alert_info

    def build_events_data(self) -> list[dict]:
        """Build events data from the alert's raw data."""
        return [dict_to_flat(self.raw_data)]
