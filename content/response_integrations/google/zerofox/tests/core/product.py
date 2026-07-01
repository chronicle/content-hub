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
from typing import MutableMapping
from TIPCommon.types import SingleJson
from ...tests.common import AlertIdNotFoundError, MOCK_DATA


class Zerofox(abc.ABC):

    def __init__(self) -> None:
        self._alerts: MutableMapping[str, SingleJson] = {}

    def add_alert(self, alert: SingleJson) -> None:
        self._alerts[alert["id"]] = alert

    def get_alerts(self) -> SingleJson:
        """Gets all alerts.

        Returns:
            Collection[SingleJson]: The alerts.
        """
        alert_data = MOCK_DATA["get_alerts"]
        alerts = list(self._alerts.values())
        alert_data["alerts"] = alerts

        return alert_data

    def get_alert(self, alert_id: int) -> SingleJson:
        if alert_id not in self._alerts:
            raise AlertIdNotFoundError(f"Mock Error: Invalid Alert ID {alert_id}")

        return self._alerts[alert_id]

    def add_note_to_alert(self, alert_id: int, note: str) -> None:
        self._alerts[alert_id]["notes"] = note

    def get_note(self, alert_id: int) -> str:
        return self._alerts[alert_id]["notes"]

    def cleanup_alerts(self) -> None:
        self._alerts = {}

    def add_evidence_to_alert(self, alert_id: int, evidence: str) -> None:
        self._alerts[alert_id]["evidence"] = evidence
