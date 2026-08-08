from __future__ import annotations

import dataclasses

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class PagerDuty:
    """Mock data container for PagerDuty integration tests."""
    incidents: SingleJson = dataclasses.field(default_factory=dict)
    users: SingleJson = dataclasses.field(default_factory=dict)
    snoozed_incidents: dict[str, SingleJson] = dataclasses.field(default_factory=dict)

    def get_incidents(self, params: SingleJson) -> SingleJson:
        """Get incidents, optionally filtered by incident_key."""
        if not self.incidents.get("incidents"):
            return {"incidents": []}

        incident_key_filter = params.get("incident_key")
        if incident_key_filter:
            filtered_incidents = [
                inc
                for inc in self.incidents["incidents"]
                if inc.get("incident_key") == incident_key_filter
            ]
            return {"incidents": filtered_incidents}
        return self.incidents

    def snooze_incident(self, incident_id: str) -> SingleJson:
        """Simulate snoozing an incident."""
        self.snoozed_incidents[incident_id] = {
            "status": "snoozed", "snooze_until": "2025-10-06T14:05:03Z"
            }
        until = "2025-10-06T14:05:03Z"
        return {
            "incident": {"id": incident_id, "status": "snoozed", "snooze_until": until}
            }

    def get_incident(self, incident_id: str) -> SingleJson:
        """Get a specific incident by ID."""
        if not self.incidents.get("incidents"):
            return {}
        for inc in self.incidents["incidents"]:
            if inc.get("id") == incident_id:
                return inc
        return {}

    def resolve_incident(self, incident_id: str) -> SingleJson:
        """Resolve a specific incident by ID."""
        if not self.incidents.get("incidents"):
            return {}
        for inc in self.incidents["incidents"]:
            if inc.get("id") == incident_id:
                inc["status"] = "resolved"
                return {"incident": inc}
        return {}

    def add_incident_note(self, incident_id: str, content: str) -> SingleJson:
        """Simulate adding a note to an incident."""
        return {"note": {"content": content}}

    def set_incidents(self, mock_incidents: SingleJson) -> None:
        """Set the mock incidents data."""
        self.incidents = mock_incidents

    def get_users(self) -> SingleJson:
        """Get all mock users."""
        return self.users

    def set_users(self, mock_users: SingleJson) -> None:
        """Set the mock users data."""
        self.users = mock_users
