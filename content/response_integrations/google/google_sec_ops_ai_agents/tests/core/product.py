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

import pathlib
import abc


class GoogleSecOpsAiAgents(abc.ABC):
    """GoogleSecOpsAiAgents mock product"""

    def __init__(self) -> None:
        super().__init__()
        self._investigations: dict[str, list] = {}
        self._triggered_investigations: dict[str, dict] = {}
        self._investigation_statuses: dict[str, dict] = {}

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
