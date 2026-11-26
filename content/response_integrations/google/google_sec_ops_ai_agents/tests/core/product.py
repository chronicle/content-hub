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


class GoogleSecOpsAiAgents(abc.ABC):
    """GoogleSecOpsAiAgents mock product"""

    def __init__(self) -> None:
        super().__init__()
        self._investigations: dict[str, list] = {}
        self._triggered_investigations: dict[str, dict] = {}
        self._investigation_statuses: dict[str, dict] = {}
        self._remediation_plans: dict[str, list[dict]] = {}
        self._generated_remediation_plans: dict[str, dict] = {}
        self._remediation_plan_details: dict[str, dict] = {}
        self._remediation_action_executions: dict[str, list[dict]] = {}

    def add_investigations(self, alert_id: str, investigations: list) -> None:
        """Add investigations to the mock product"""
        self._investigations[alert_id] = investigations

    def get_investigations(self, alert_id: str) -> list:
        """Get investigations from the mock product"""
        return self._investigations.get(alert_id, [])

    def cleanup_investigations(self) -> None:
        """Cleanup investigations from the mock product"""
        self._investigations = {}

    def add_triggered_investigation(self, alert_id: str, investigation_data: dict) -> None:
        """Add a triggered investigation to the mock product"""
        self._triggered_investigations[alert_id] = investigation_data

    def trigger_investigation(self, alert_id: str) -> dict:
        """Trigger an investigation in the mock product"""
        return self._triggered_investigations.get(alert_id, {})

    def add_investigation_status(self, investigation_name: str, status_data: dict) -> None:
        """Add an investigation status to the mock product"""
        self._investigation_statuses[investigation_name] = status_data

    def get_investigation_status(self, investigation_name: str) -> dict:
        """Get an investigation status from the mock product"""
        return self._investigation_statuses.get(investigation_name, {})

    def add_remediation_plans(self, alert_id: str, plans: list[dict]) -> None:
        """Add existing remediation plans for an alert."""
        self._remediation_plans[alert_id] = plans

    def get_remediation_plans(self, alert_id: str) -> list[dict]:
        """Get existing remediation plans for an alert."""
        return self._remediation_plans.get(alert_id, [])

    def add_generated_remediation_plan(self, alert_id: str, plan_data: dict) -> None:
        """Add generated remediation plan response for an alert."""
        self._generated_remediation_plans[alert_id] = plan_data

    def get_generated_remediation_plan(self, alert_id: str) -> dict:
        """Get generated remediation plan response for an alert."""
        return self._generated_remediation_plans.get(alert_id, {})

    def add_remediation_plan_details(
        self, plan_name_or_id: str | int, plan_data: dict
    ) -> None:
        """Add details for a specific remediation plan by name or ID."""
        key = str(plan_name_or_id)
        self._remediation_plan_details[key] = plan_data
        short_id = key.split("/")[-1] if "/" in key else key
        self._remediation_plan_details[short_id] = plan_data
        try:
            self._remediation_plan_details[int(short_id)] = plan_data
        except (ValueError, TypeError):
            pass

    def get_remediation_plan_details(self, plan_name_or_id: str | int) -> dict:
        """Get details for a specific remediation plan by name or ID."""
        if plan_name_or_id in self._remediation_plan_details:
            return self._remediation_plan_details[plan_name_or_id]
        key = str(plan_name_or_id)
        if key in self._remediation_plan_details:
            return self._remediation_plan_details[key]
        short_id = key.split("/")[-1] if "/" in key else key
        return self._remediation_plan_details.get(short_id, {})

    def add_remediation_action_executions(
        self, plan_name_or_id: str | int, executions: list[dict]
    ) -> None:
        """Add action executions for a specific remediation plan."""
        key = str(plan_name_or_id)
        self._remediation_action_executions[key] = executions
        short_id = key.split("/")[-1] if "/" in key else key
        self._remediation_action_executions[short_id] = executions
        try:
            self._remediation_action_executions[int(short_id)] = executions
        except (ValueError, TypeError):
            pass

    def get_remediation_action_executions(
        self, plan_name_or_id: str | int
    ) -> list[dict]:
        """Get action executions for a specific remediation plan."""
        if plan_name_or_id in self._remediation_action_executions:
            return self._remediation_action_executions[plan_name_or_id]
        key = str(plan_name_or_id)
        if key in self._remediation_action_executions:
            return self._remediation_action_executions[key]
        short_id = key.split("/")[-1] if "/" in key else key
        return self._remediation_action_executions.get(short_id, [])

    def cleanup_remediation(self) -> None:
        """Cleanup all remediation plan mocks."""
        self._remediation_plans.clear()
        self._generated_remediation_plans.clear()
        self._remediation_plan_details.clear()
        self._remediation_action_executions.clear()

