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

from typing import TYPE_CHECKING

from proofpoint_cloud_threat_response.core.data_models import ProofpointIncident, ProofpointMessage

if TYPE_CHECKING:
    from TIPCommon.types import SingleJson


class ProofpointCTRParser:

    def parse_incidents(self, raw_data: SingleJson) -> list[ProofpointIncident]:
        """Parse incidents."""
        return [
            ProofpointIncident.from_json(item) for item in raw_data.get("incidents", [])
        ]

    def parse_messages(self, raw_data: SingleJson) -> list[ProofpointMessage]:
        """Parse messages."""
        return [
            ProofpointMessage.from_json(item) for item in raw_data.get("messages", [])
        ]
