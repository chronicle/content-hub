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

from typing import Any
import dataclasses

from TIPCommon.transformation import dict_to_flat
from TIPCommon.types import SingleJson


@dataclasses.dataclass(frozen=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return dataclasses.asdict(self)

    def to_flat(self) -> dict[str, Any]:
        return dict_to_flat(self.to_json()["raw_data"])


@dataclasses.dataclass(frozen=True)
class ListSecurityPolicy(BaseModel):
    """Class to create data model for List Security Policy"""

    policy_id: str
    name: str
    rules: str
    fingerprint: str

    @classmethod
    def from_json(cls, policy_json: SingleJson) -> ListSecurityPolicy:
        """Create a ListSecurityPolicy object from JSON data.

        Args:
            policy_json (SingleJson): Policy data json response from API.

        Returns:
            ListSecurityPolicy: ListSecurityPolicy object.
        """
        return cls(
            raw_data=policy_json,
            policy_id=policy_json["id"],
            name=policy_json["name"],
            rules=policy_json["rules"],
            fingerprint=policy_json["fingerprint"],
        )


@dataclasses.dataclass(frozen=True)
class CreateOrUpdateSecurityPolicy(BaseModel):
    """Class to create data model for Create or Update Security Policy"""

    policy_id: str
    name: str
    status: str
    progress: int
    start_time: str
    error: SingleJson

    @classmethod
    def from_json(cls, policy_json: SingleJson) -> CreateOrUpdateSecurityPolicy:
        """Create a SecurityPolicy object from JSON data.

        Args:
            policy_json (SingleJson): Policy data json response from API.

        Returns:
            CreateOrUpdateSecurityPolicy: CreateOrUpdateSecurityPolicy object.
        """
        return cls(
            raw_data=policy_json,
            policy_id=policy_json["id"],
            name=policy_json["name"],
            status=policy_json["status"],
            progress=policy_json["progress"],
            start_time=policy_json.get("startTime"),
            error=policy_json.get("error", {}),
        )
