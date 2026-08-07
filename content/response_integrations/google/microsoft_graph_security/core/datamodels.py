from __future__ import annotations

import copy

import dataclasses
from datetime import datetime

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time

from TIPCommon.transformation import convert_list_to_comma_string, dict_to_flat
from TIPCommon.types import SingleJson
from . import constants


class Alert:
    def __init__(
        self,
        raw_data,
        id=None,
        tags=None,
        assignedTo=None,
        category=None,
        comments=None,
        confidence=None,
        createdDateTime=None,
        description=None,
        eventDateTime=None,
        lastModifiedDateTime=None,
        severity=None,
        status=None,
        title=None,
        vendor=None,
        vendorInformation=None,
        provider=None,
        malwareStates=None,
        hostStates=None,
        fileStates=None,
        networkConnections=None,
        recommendedActions=None,
        registryKeyStates=None,
        userStates=None,
        vulnerabilityStates=None,
        processes=None,
        triggers=None,
        cloudAppStates=None,
        sourceMaterials=None,
        detectionIds=None,
        activityGroupName=None,
        feedback=None,
        **kwargs
    ):
        self.raw_data = raw_data
        self.id = id
        self.tags = tags
        self.assigned_to = assignedTo
        self.category = category
        self.comments = comments
        self.confidence = confidence
        self.created_datetime = createdDateTime
        self.description = description
        self.event_datetime = eventDateTime
        self.last_modified_datetime = lastModifiedDateTime or kwargs.get(
            "lastUpdateDateTime"
        )
        self.severity = severity
        self.status = status
        self.title = title
        self.vendor = vendor
        self.provider = provider
        self.vendorInformation = vendorInformation
        self.malware_states = malwareStates
        self.host_states = hostStates
        self.file_states = fileStates
        self.network_connections = networkConnections
        self.recommended_actions = recommendedActions
        self.registry_key_states = registryKeyStates
        self.user_states = userStates
        self.vulnerability_states = vulnerabilityStates
        self.cloud_app_states = cloudAppStates
        self.triggers = triggers
        self.processes = processes
        self.feedback = feedback
        self.activity_group_name = activityGroupName
        self.detection_ids = detectionIds
        self.source_materials = sourceMaterials

        try:
            self.event_datetime_ms = convert_string_to_unix_time(eventDateTime)
        except Exception:
            self.event_datetime_ms = 1

        try:
            self.created_datetime_ms = convert_string_to_unix_time(createdDateTime)
        except Exception:
            self.created_datetime_ms = 1

        try:
            self.last_modified_datetime_ms = convert_string_to_unix_time(
                self.last_modified_datetime
            )
        except Exception:
            self.last_modified_datetime_ms = 1

    def as_json(self):
        return self.raw_data

    def as_event(self):
        event_data = copy.deepcopy(self.raw_data)
        event_data["event_class"] = "Alert"
        if event_data.get("createdDateTime"):
            event_data["iso_timestamp"] = event_data.get("createdDateTime")
        elif event_data.get("timestamp"):
            _dt = datetime.fromtimestamp(int(event_data.get("timestamp")) / 1000)
            event_data["iso_timestamp"] = _dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        for state in constants.EVENT_STATES:
            event_data.pop(state, None)
        return dict_to_flat(event_data)

    def as_event_v2(self) -> list[SingleJson]:
        """Converts Evidences into Google Secops events.

        Returns:
            list[SingleJson]: List of dict containing events.
        """
        events = []
        alert_metadata = copy.deepcopy(self.raw_data)
        for evidence in alert_metadata.pop("evidence"):
            evidence["event_class"] = "Evidence"
            evidence.update(alert_metadata)
            formatted_event = dict_to_flat(evidence)
            events.append(formatted_event)

        return events

    def as_csv(self):
        return {
            "Alert ID": self.id,
            "Title": self.title,
            "Assigned To": self.assigned_to,
            "Category": self.category,
            "Confidence": self.confidence,
            "Created At": self.created_datetime,
            "Description": self.description,
            "Event Created At": self.event_datetime,
            "Last Modified At": self.last_modified_datetime,
            "Severity": self.severity,
            "Status": self.status,
            "Vendor": self.vendor,
            "Provider": self.provider,
            "Number of Related Malware": (
                len(self.malware_states) if self.malware_states else 0
            ),
            "Number of Related Hosts": len(self.host_states) if self.host_states else 0,
            "Number of Related Files": len(self.file_states) if self.file_states else 0,
            "Number of Related Network Connections": (
                len(self.network_connections) if self.network_connections else 0
            ),
            "Number of Related User Accounts": (
                len(self.user_states) if self.user_states else 0
            ),
            "Number of Related Vulnerabilities": (
                len(self.vulnerability_states) if self.vulnerability_states else 0
            ),
            "Recommended Actions": (
                "\n".join(self.recommended_actions)
                if self.recommended_actions
                else None
            ),
        }

    def as_extension(self):
        return dict_to_flat(
            {
                "source_materials": self.source_materials,
                "tags": self.tags,
                "status": self.status,
                "recommended_actions": self.recommended_actions,
                "feedback": self.feedback,
                "confidence": self.confidence,
                "category": self.category,
                "assigned_to": self.assigned_to,
                "activity_group_name": self.activity_group_name,
                "detection_ids": self.detection_ids,
            }
        )

    @property
    def siemplify_severity(self):
        return constants.SEVERITY_MAP.get(self.severity, -1)


@dataclasses.dataclass(frozen=True)
class Incident:
    """Class to create datamodel for Incident"""

    raw_data: SingleJson
    incident_id: str
    system_tags: list[str]
    status: str
    severity: str
    created_date_time: str
    last_update_date_time: str
    assigned_to: str | None = None
    comments: list[str] | None = None
    display_name: str | None = None
    description: str | None = None
    summary: str | None = None

    @classmethod
    def from_json(cls, incident_data: SingleJson) -> Incident:
        """Create a Incident instance from JSON data.

        Args:
            incident_data(SingleJson): MsGraph Incidents data.

        Returns:
            Incident: Incident object.
        """
        return cls(
            raw_data=incident_data,
            incident_id=incident_data["id"],
            display_name=incident_data["displayName"],
            description=incident_data["description"],
            summary=incident_data["summary"],
            system_tags=incident_data["systemTags"],
            status=incident_data["status"],
            severity=incident_data["severity"],
            assigned_to=incident_data["assignedTo"],
            comments=incident_data["comments"],
            created_date_time=incident_data["createdDateTime"],
            last_update_date_time=incident_data["lastUpdateDateTime"],
        )

    def to_table(self) -> SingleJson:
        """Returns dict object to create case wall table.

        Returns:
            SingleJson: dict object for table.
        """
        return {
            "Incident ID": self.incident_id,
            "Title": self.display_name,
            "Description": self.description,
            "Summary": self.summary,
            "System Tags": convert_list_to_comma_string(self.system_tags),
            "Status": self.status,
            "Severity": self.severity,
            "Assigned To": self.assigned_to,
            "Comments": convert_list_to_comma_string(self.comments),
            "Created Time": self.created_date_time,
            "Last Modified Time": self.last_update_date_time,
        }

    def to_json(self) -> SingleJson:
        return self.raw_data
