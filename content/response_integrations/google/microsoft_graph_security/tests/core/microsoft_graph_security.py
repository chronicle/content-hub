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

import dataclasses

from TIPCommon.types import SingleJson

from microsoft_graph_security.core.datamodels import Incident


@dataclasses.dataclass
class MicrosoftGraphSecurity(abc.ABC):
    incidents: dict[str, Incident] = dataclasses.field(default_factory=dict)

    def add_incident(self, incident: Incident) -> None:
        self.incidents[incident.incident_id] = incident

    def get_incident(self, incident_id: str) -> Incident:
        return self.incidents[incident_id]

    def add_incidents(self, incidents: list[Incident]) -> None:
        self.incidents["list_incidents"] = incidents

    def list_incidents(self) -> SingleJson:
        return self.incidents["list_incidents"]
