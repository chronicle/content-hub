# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations
import abc

import uuid
from typing import Any, MutableMapping

from TIPCommon.types import SingleJson


class MicrosoftDefenderATP(abc.ABC):
    def __init__(self) -> None:
        self._machines: MutableMapping[str, SingleJson] = {}
        self._live_response_actions: MutableMapping[str, Any] = {}
        self._vulnerabilities: MutableMapping[str, list[SingleJson]] = {}
        self._recommendations: MutableMapping[str, SingleJson] = {}
        self._user_related_alerts: MutableMapping[str, Any] = {}
        self._alerts: list[SingleJson] = []
        self._file_alerts: dict[str, list[SingleJson]] = {}
        self._file_machines: dict[str, list[SingleJson]] = {}
        self._logon_users: dict[str, list[SingleJson]] = {}
        self._machine_alerts: dict[str, list[SingleJson]] = {}
        self._tasks: dict[str, SingleJson] = {}
        self._indicators: list[SingleJson] = []
        self._submitted_indicators: list[SingleJson] = []
        self._hunting_query_result: SingleJson = {"Results": []}
        self._file_info: dict[str, SingleJson] = {}
        self._file_stats: dict[str, SingleJson] = {}
        self._updateable_alerts: dict[str, SingleJson] = {}

    # -------------------------------------------------------------------------
    # Vulnerabilities
    # -------------------------------------------------------------------------

    def add_vulnerability(self, vulnerability_data: SingleJson) -> None:
        """Add vulnerability data."""
        machine_id: str = vulnerability_data["machineId"]
        if machine_id not in self._vulnerabilities:
            self._vulnerabilities[machine_id] = []
        self._vulnerabilities[machine_id].append(vulnerability_data)

    def cleanup_vulnerabilities(self) -> None:
        """Cleanup vulnerabilities data."""
        self._vulnerabilities = {}

    def get_machine_vulnerabilities(self, machine_id: str) -> SingleJson:
        """Get machine vulnerabilities by machine ID."""
        return self._vulnerabilities.get(machine_id, [])

    # -------------------------------------------------------------------------
    # Recommendations
    # -------------------------------------------------------------------------

    def add_recommendation(self, recommendation_data: SingleJson) -> None:
        """Add recommendation data."""
        self._recommendations[recommendation_data["id"]] = recommendation_data

    def get_recommendations_by_machine_id(self, machine_id: str) -> list[SingleJson]:
        """Get recommendations by machine ID."""
        return [
            rec for rec in self._recommendations.values()
            if rec.get("machineId") == machine_id
        ]

    # -------------------------------------------------------------------------
    # User-related alerts
    # -------------------------------------------------------------------------

    def add_user_related_alert(
        self,
        alert_data: SingleJson,
        fail_request: bool = False,
    ) -> None:
        """Adds mock alert data for user testing.

        Args:
            alert_data(SingleJson): The alert data to add.
            fail_request(bool): Whether to simulate a failed request.
        """
        user_id: str | None = alert_data.get("alertUser", {}).get("accountName")
        if not user_id and "actor" in alert_data:
            user_id = alert_data["actor"]["accountId"]
        if user_id not in self._user_related_alerts:
            self._user_related_alerts[user_id] = {"alerts": [], "failed": False}

        if fail_request:
            self._user_related_alerts[user_id]["failed"] = True
        else:
            self._user_related_alerts[user_id]["alerts"].append(alert_data)

    def get_user_related_alerts(
        self,
        user_id: str,
    ) -> SingleJson | None:
        """Get user related alerts by user ID."""
        return self._user_related_alerts.get(user_id)

    # -------------------------------------------------------------------------
    # Machines
    # -------------------------------------------------------------------------

    def add_machine(self, machine_data: SingleJson) -> None:
        """Add a machine by ID."""
        self._machines[machine_data["id"]] = machine_data

    def cleanup_machines(self) -> None:
        """Remove all machines."""
        self._machines = {}

    def get_machine_by_id(self, machine_id: str) -> SingleJson | None:
        """Return a machine dict by its ID."""
        return self._machines.get(machine_id)

    def get_machine_by_ip(self, ip: str) -> SingleJson | None:
        """Get machine by IP address."""
        for machine in self._machines.values():
            if ip == machine.get("lastIpAddress"):
                return machine
        return None

    def get_machine_by_hostname(self, hostname: str) -> SingleJson | None:
        """Get machine by hostname (startswith match, case-insensitive)."""
        for machine in self._machines.values():
            if machine.get("computerDnsName", "").lower().startswith(hostname.lower()):
                return machine
        return None

    def get_all_machines(self) -> list[SingleJson]:
        """Return all machines."""
        return list(self._machines.values())

    # -------------------------------------------------------------------------
    # Live response actions
    # -------------------------------------------------------------------------

    def add_live_response_action(self, machine_id: str, command: str) -> str:
        """Simulates initiating a live response action.

        Args:
            machine_id: The ID of the machine.
            command: The command to run.

        Returns:
            The action ID.
        """
        action_id = str(uuid.uuid4())
        self._live_response_actions[action_id] = {
            "id": action_id,
            "type": "RunLiveResponse",
            "requestor": "test@contoso.com",
            "status": "Pending",
            "machineId": machine_id,
            "creationDateTimeUtc": "2024-01-01T12:00:00.000Z",
            "lastUpdateDateTimeUtc": "2024-01-01T12:00:00.000Z",
            "commands": [{"index": 0, "command": command}],
        }
        return action_id

    def get_live_response_action(self, action_id: str) -> SingleJson | None:
        """Get live response action by ID.

        Args:
            action_id: The ID of the action.
        """
        return self._live_response_actions.get(action_id)

    # -------------------------------------------------------------------------
    # Alerts (global list, used by ListAlerts / test_connectivity)
    # -------------------------------------------------------------------------

    def add_alert(self, alert_data: SingleJson) -> None:
        """Add a global alert to the product store."""
        self._alerts.append(alert_data)

    def get_alerts(self) -> list[SingleJson]:
        """Return all stored alerts."""
        return list(self._alerts)

    def cleanup_alerts(self) -> None:
        """Clear all stored alerts."""
        self._alerts = []

    # -------------------------------------------------------------------------
    # File-related alerts
    # -------------------------------------------------------------------------

    def add_file_alert(self, file_hash: str, alert_data: SingleJson) -> None:
        """Add an alert associated with a file hash."""
        self._file_alerts.setdefault(file_hash.lower(), []).append(alert_data)

    def get_file_alerts(self, file_hash: str) -> list[SingleJson]:
        """Return alerts for a given file hash."""
        return self._file_alerts.get(file_hash.lower(), [])

    # -------------------------------------------------------------------------
    # File-related machines
    # -------------------------------------------------------------------------

    def add_file_machine(self, file_hash: str, machine_data: SingleJson) -> None:
        """Add a machine associated with a file hash."""
        self._file_machines.setdefault(file_hash.lower(), []).append(machine_data)

    def get_file_machines(self, file_hash: str) -> list[SingleJson]:
        """Return machines for a given file hash."""
        return self._file_machines.get(file_hash.lower(), [])

    # -------------------------------------------------------------------------
    # Machine logon users
    # -------------------------------------------------------------------------

    def add_logon_user(self, machine_id: str, user_data: SingleJson) -> None:
        """Add a logon user for a machine."""
        self._logon_users.setdefault(machine_id, []).append(user_data)

    def get_logon_users(self, machine_id: str) -> list[SingleJson]:
        """Return logon users for a machine."""
        return self._logon_users.get(machine_id, [])

    # -------------------------------------------------------------------------
    # Machine-related alerts
    # -------------------------------------------------------------------------

    def add_machine_alert(self, machine_id: str, alert_data: SingleJson) -> None:
        """Add an alert related to a machine."""
        self._machine_alerts.setdefault(machine_id, []).append(alert_data)

    def get_machine_alerts(self, machine_id: str) -> list[SingleJson]:
        """Return alerts related to a machine."""
        return self._machine_alerts.get(machine_id, [])

    # -------------------------------------------------------------------------
    # Machine tasks (isolate / unisolate / AV scan / stop-quarantine)
    # -------------------------------------------------------------------------

    def create_task(
        self,
        task_type: str,
        machine_id: str,
        status: str = "Pending",
        comment: str = "test",
    ) -> SingleJson:
        """Create and store a task, returning its data dict."""
        task_id = str(uuid.uuid4())
        machine = self._machines.get(machine_id, {})
        task_data: SingleJson = {
            "id": task_id,
            "type": task_type,
            "requestor": "test@contoso.com",
            "requestorComment": comment,
            "status": status,
            "machineId": machine_id,
            "computerDnsName": machine.get("computerDnsName", "unknown"),
            "creationDateTimeUtc": "2024-01-01T12:00:00.000Z",
            "lastUpdateDateTimeUtc": "2024-01-01T12:00:00.000Z",
            "cancellationRequestor": None,
            "cancellationComment": None,
            "cancellationDateTimeUtc": None,
            "errorHResult": 0,
            "scope": None,
        }
        self._tasks[task_id] = task_data
        return task_data

    def add_task(self, task_data: SingleJson) -> None:
        """Add a pre-built task dict."""
        self._tasks[task_data["id"]] = task_data

    def get_task(self, task_id: str) -> SingleJson | None:
        """Return a task by ID."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[SingleJson]:
        """Return all tasks."""
        return list(self._tasks.values())

    # -------------------------------------------------------------------------
    # Indicators
    # -------------------------------------------------------------------------

    def add_indicator(self, indicator_data: SingleJson) -> None:
        """Add an existing indicator."""
        self._indicators.append(indicator_data)

    def get_indicators(self) -> list[SingleJson]:
        """Return all existing indicators."""
        return list(self._indicators)

    def record_submitted_indicator(self, indicator_data: SingleJson) -> None:
        """Record a newly submitted indicator."""
        self._submitted_indicators.append(indicator_data)

    def get_submitted_indicators(self) -> list[SingleJson]:
        """Return all submitted indicators."""
        return list(self._submitted_indicators)

    # -------------------------------------------------------------------------
    # Advanced hunting query
    # -------------------------------------------------------------------------

    def set_hunting_query_result(self, result: SingleJson) -> None:
        """Set the result for advanced hunting queries."""
        self._hunting_query_result = result

    def get_hunting_query_result(self) -> SingleJson:
        """Return the stored hunting query result."""
        return self._hunting_query_result

    # -------------------------------------------------------------------------
    # File info / stats (for EnrichEntities)
    # -------------------------------------------------------------------------

    def set_file_info(self, file_hash: str, info: SingleJson) -> None:
        """Store file info for a given hash."""
        self._file_info[file_hash.lower()] = info

    def get_file_info(self, file_hash: str) -> SingleJson:
        """Return file info for a given hash."""
        return self._file_info.get(file_hash.lower(), {})

    def set_file_stats(self, file_hash: str, stats: SingleJson) -> None:
        """Store file stats for a given hash."""
        self._file_stats[file_hash.lower()] = stats

    def get_file_stats_data(self, file_hash: str) -> SingleJson:
        """Return file stats for a given hash."""
        return self._file_stats.get(file_hash.lower(), {})

    # -------------------------------------------------------------------------
    # Alert update (for UpdateAlert)
    # -------------------------------------------------------------------------

    def add_updateable_alert(self, alert_data: SingleJson) -> None:
        """Store an alert that can be patched via update_alert."""
        self._updateable_alerts[alert_data["id"]] = dict(alert_data)

    def get_updateable_alert(self, alert_id: str) -> SingleJson | None:
        """Return an alert by ID for patching."""
        return self._updateable_alerts.get(alert_id)
