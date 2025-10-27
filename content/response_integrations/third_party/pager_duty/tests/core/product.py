from __future__ import annotations

import dataclasses

from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class PagerDuty:
    incidents: SingleJson = dataclasses.field(default_factory=dict)
    users: SingleJson = dataclasses.field(default_factory=dict)
    snoozed_incidents: dict[str, SingleJson] = dataclasses.field(default_factory=dict)

    def get_incidents(self, params: SingleJson) -> SingleJson:
        """
        Returns incidents, filtering them based on provided parameters to
        simulate the real API behavior.
        """
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
        self.snoozed_incidents[incident_id] = {
            "status": "snoozed", "snooze_until": "2025-10-06T14:05:03Z"
            }
        return {
            "incident": {"id": incident_id, "status": "snoozed", "snooze_until": "2025-10-06T14:05:03Z"}
            }

    def set_incidents(self, mock_incidents: SingleJson) -> None:
        self.incidents = mock_incidents

    def get_users(self) -> SingleJson:
        return self.users

    def set_users(self, mock_users: SingleJson) -> None:
        self.users = mock_users
