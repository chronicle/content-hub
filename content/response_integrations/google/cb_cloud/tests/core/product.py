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


@dataclasses.dataclass
class Product(abc.ABC):
    _alerts_map: dict[str, SingleJson] = dataclasses.field(default_factory=dict)
    _observations: list[SingleJson] = dataclasses.field(default_factory=list)
    _observation_details: list[SingleJson] = dataclasses.field(default_factory=list)

    def add_alerts(self, alerts: list[SingleJson]) -> None:
        self._alerts_map.update({alert_["id"]: alert_ for alert_ in alerts})

    def list_alerts(self, start: int, rows: int) -> list[SingleJson]:
        return list(self._alerts_map.values())[start - 1: start + rows]

    def add_observations(self, observations: list[SingleJson]) -> None:
        self._observations.extend(observations)

    def list_observations(self) -> list[SingleJson]:
        return self._observations

    def add_observation_details(self, observations: list[SingleJson]) -> None:
        self._observation_details.extend(observations)

    def list_observation_details(self) -> list[SingleJson]:
        return self._observation_details
