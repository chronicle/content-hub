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

from TIPCommon.types import SingleJson

from microsoft365_defender.core.datamodels import Alert, AlertWithEvidence, Device, Incident


class Microsoft365DefenderParser:
    def __init__(self, logger=None):
        self.logger = logger

    def build_incident_object(self, raw_data, alerts=None):
        return Incident(
            raw_data=raw_data,
            incident_id=raw_data.get("incidentId", raw_data.get("id")),
            incident_name=raw_data.get("incidentName", raw_data.get("displayName")),
            severity=raw_data.get("severity"),
            classification=raw_data.get("classification"),
            created_time=raw_data.get("createdDateTime"),
            last_update_time=raw_data.get("lastUpdateDateTime"),
            alerts=alerts,
        )

    def _extract_title(self, raw_data):
        title_keys = ["title", "alertTitle", "displayName"]
        for key in title_keys:
            if raw_data.get(key):
                return raw_data.get(key)

        return None

    def build_alert_object(self, raw_data):
        title = self._extract_title(raw_data)
        return Alert(
            raw_data=raw_data,
            alert_id=raw_data.get("alertId", raw_data.get("id")),
            incident_id=raw_data.get("incidentId"),
            entities=raw_data.get("entities"),
            devices=raw_data.get("devices"),
            title=title,
            severity=raw_data.get("severity"),
            first_activity=(
                raw_data.get("firstActivity")
                or raw_data.get("firstActivityDateTime")
                or raw_data.get("createdDateTime")
            ),
            last_activity=(
                raw_data.get("lastActivity")
                or raw_data.get("lastActivityDateTime")
                or raw_data.get("lastUpdateDateTime")
            ),
            description=raw_data.get("description"),
        )

    def build_alert_with_evidence_object(self, raw_data: SingleJson) -> AlertWithEvidence:
        """
        Build AlertWithEvidence object from raw data.

        Args:
            raw_data (SingleJson): Dict representing raw alert data.

        Returns:
            AlertWithEvidence: AlertWithEvidence object.
        """
        title = self._extract_title(raw_data)
        evidences = [
            *(raw_data.get("evidence") or []),
            *(raw_data.get("evidences") or []),
            *(raw_data.get("assets") or []),
        ]
        return AlertWithEvidence(
            raw_data=raw_data,
            alert_id=raw_data.get("id", raw_data.get("alertId")),
            incident_id=raw_data.get("incidentId", raw_data.get("id")),
            title=title,
            severity=raw_data.get("severity"),
            assignee=raw_data.get("assignedTo"),
            first_activity=(
                raw_data.get("firstActivityDateTime")
                or raw_data.get("firstActivity")
                or raw_data.get("createdDateTime")
            ),
            last_activity=(
                raw_data.get("lastActivityDateTime")
                or raw_data.get("lastActivity")
                or raw_data.get("lastUpdateDateTime")
            ),
            description=raw_data.get("description"),
            evidences=evidences,
        )

    def build_device_objects(self, raw_data, data_root_key: str = "Results"):
        return [
            self.build_device_object(item) for item in raw_data.get(data_root_key, [])
        ]

    def build_device_object(self, raw_data):
        return Device(raw_data=raw_data)
