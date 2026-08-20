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
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class Agent:
    """Dataclass representing a SentinelOne Agent/Endpoint."""

    id: str
    uuid: str
    network_status: str
    computer_name: str
    last_active_date: Optional[str] = None
    os_type: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        """Convert Agent instance to a JSON-serializable dictionary."""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "network_status": self.network_status,
            "computer_name": self.computer_name,
            "last_active_date": self.last_active_date,
            "os_type": self.os_type,
            "raw_data": self.raw_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Agent:
        """Construct Agent instance from raw SentinelOne API response dictionary."""
        return cls(
            id=str(data.get("id", "")),
            uuid=str(data.get("uuid", "")),
            network_status=data.get("networkStatus") or data.get("network_status") or "unknown",
            computer_name=data.get("computerName") or data.get("computer_name") or "",
            last_active_date=data.get("lastActiveDate") or data.get("last_active_date"),
            os_type=data.get("osType") or data.get("os_type"),
            raw_data=data,
        )
