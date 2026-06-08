# Copyright 2025 Google LLC
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

import dataclasses
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


@dataclasses.dataclass(slots=True)
class EnrichmentProduct:
    case_metadata: SingleJson = dataclasses.field(default_factory=dict)
    alerts_full_details: SingleJson = dataclasses.field(default_factory=dict)
    _cached_mock_siemplify: Any = dataclasses.field(default=None, init=False)

    def set_case_metadata(self, mock_data: SingleJson) -> None:
        self.case_metadata = mock_data

    def set_alerts_full_details(self, mock_data: SingleJson) -> None:
        self.alerts_full_details = mock_data

    def get_case_metadata(self) -> SingleJson:
        return self.case_metadata

    def get_alerts_full_details(self) -> SingleJson:
        return self.alerts_full_details
