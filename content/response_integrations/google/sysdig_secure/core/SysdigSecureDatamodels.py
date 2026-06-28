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

import dataclasses
from typing import Any

from TIPCommon.transformation import dict_to_flat
from TIPCommon.types import SingleJson

from sysdig_secure.core.SysdigSecureUtils import convert_nanoseconds_to_milliseconds


@dataclasses.dataclass(frozen=True)
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return dataclasses.asdict(self)

    def to_flat(self) -> dict[str, Any]:
        return dict_to_flat(self.to_json()["raw_data"])


@dataclasses.dataclass(frozen=True)
class BaseObject(BaseModel):
    """Class to create data model for Base Object"""

    @classmethod
    def from_json(cls, raw_data: SingleJson) -> BaseObject:
        """Create a BaseObject object from JSON data

        Args:
            raw_data (SingleJson): raw data to create BaseObject from

        Returns:
            BaseObject: Base object
        """
        return cls(raw_data=raw_data)


@dataclasses.dataclass(frozen=True)
class Event(BaseModel):
    """Class to create data model for Event object"""
    raw_flat_data: dict
    event_id: str
    alert_id: str
    rule_name: str
    output: str
    timestamp: int
    severity: int

    @classmethod
    def from_json(cls, raw_data: dict) -> Event:
        """
        Create Event object from raw json data

        Args:
            raw_data (dict): raw data of event

        Returns:
            Event: Event object
        """
        return cls(
            raw_data=raw_data,
            raw_flat_data=dict_to_flat(raw_data),
            event_id=raw_data.get("id"),
            alert_id=raw_data.get("id"),
            rule_name=raw_data.get("content", {}).get("ruleName"),
            output=raw_data.get("content", {}).get("output"),
            timestamp=convert_nanoseconds_to_milliseconds(raw_data.get("timestamp", 0)),
            severity=raw_data.get("severity")
        )
