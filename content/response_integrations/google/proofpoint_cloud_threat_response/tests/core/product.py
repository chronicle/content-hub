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
import json

from proofpoint_cloud_threat_response.core.data_models import (
    ProofpointIncident,
    ProofpointMessage,
)


class ProofpointCloudThreatResponse(abc.ABC):
    def __init__(self) -> None:
        self._incidents: MutableMapping[str, list[ProofpointIncident]] = {}
        self._messages: MutableMapping[str, list[ProofpointMessage]] = {}

    def add_incidents(self, query: str, incidents: list[ProofpointIncident]) -> None:
        self._incidents[query] = incidents

    def get_incidents(self, query: str) -> list[ProofpointIncident]:
        """Get incidents from the mock product.
        Args:
            query: The query to filter incidents.
        Returns:
            A list of incidents.
        """
        try:
            filters = json.loads(query)
            filters.pop("time_range_filter", None)
            modified_query = json.dumps(filters, sort_keys=True)
            return self._incidents.get(modified_query, [])
        except (json.JSONDecodeError, AttributeError):
            return self._incidents.get(query, [])

    def cleanup_incidents(self) -> None:
        self._incidents.clear()

    def add_messages(self, incident_id: str, messages: list[ProofpointMessage]) -> None:
        self._messages[incident_id] = messages

    def get_messages(self, incident_id: str) -> list[ProofpointMessage]:
        return self._messages.get(incident_id, [])

    def cleanup_messages(self) -> None:
        self._messages.clear()
