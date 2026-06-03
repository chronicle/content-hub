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

"""ThreatConnect product mock for high-fidelity test cases."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.data_models import IndicatorData


@dataclasses.dataclass(slots=True)
class ThreatConnectProduct:
    """In-memory mock product database representing ThreatConnect backend."""

    indicators: dict[str, IndicatorData] = dataclasses.field(default_factory=dict)

    def get_indicator(self, summary: str) -> IndicatorData | None:
        """Retrieve mock indicator by its summary value (case-insensitive)."""
        key = summary.lower()
        return self.indicators.get(key)

    def add_indicator(self, summary: str, indicator: IndicatorData) -> None:
        """Add a mock indicator to the in-memory database."""
        self.indicators[summary.lower()] = indicator
