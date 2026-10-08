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

from soar_sdk.SiemplifyUtils import convert_string_to_unix_time
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
class Alert(BaseModel):
    """Class to create data model for Alert object"""

    raw_flat_data: dict
    alert_id: str
    status: str
    title: str
    created_at: str
    severity: int
    alert_type: str
    alert_summary: str
    aggregated_under_id: str
    monitor_name: str
    topics: [Topic]

    @classmethod
    def from_json(cls, raw_data: dict, topics: [Topic]) -> Alert:
        """Create Alert object from raw json data

        Args:
            raw_data (dict): raw data of alert
            topics ([Topic]): list of Topic objects

        Returns:
            Alert: Alert object
        """
        return cls(
            raw_data=raw_data,
            raw_flat_data=dict_to_flat(raw_data),
            alert_id=raw_data.get("id"),
            status=raw_data.get("status"),
            title=raw_data.get("title"),
            created_at=convert_string_to_unix_time(raw_data.get("created_at")),
            severity=raw_data.get("severity"),
            alert_type=raw_data.get("alert_type"),
            alert_summary=raw_data.get("alert_summary"),
            aggregated_under_id=raw_data.get("aggregated_under_id"),
            monitor_name=raw_data.get("monitor_name"),
            topics=topics,
        )


@dataclasses.dataclass(frozen=True)
class Topic(BaseModel):
    """Class to create data model for Topic object"""

    @classmethod
    def from_json(cls, raw_data: dict) -> Topic:
        """Create Topic object from raw json data

        Args:
            raw_data (dict): raw data of alert

        Returns:
            Topic: Topic object
        """
        return cls(raw_data=raw_data)
