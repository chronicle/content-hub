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


@dataclasses.dataclass
class BaseModel:
    raw_data: SingleJson

    def to_json(self) -> SingleJson:
        return dataclasses.asdict(self)

    def to_flat(self) -> dict[str, Any]:
        return dict_to_flat(self.to_json()["raw_data"])


@dataclasses.dataclass
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


@dataclasses.dataclass
class Alert(BaseModel):
    """Class to create data model for Alert object"""

    raw_flat_data: dict
    alert_id: str
    name: str
    description: str
    status: str
    severity: str
    modified: str
    alert_type: str
    external_id: str
    source_name: str
    events: [Event]

    @classmethod
    def from_json(cls, raw_data: dict) -> Alert:
        """Create Alert object from raw json data

        Args:
            raw_data (dict): raw data of alert

        Returns:
            Alert: Alert object
        """
        return cls(
            raw_data=raw_data,
            raw_flat_data=dict_to_flat(raw_data),
            alert_id=raw_data.get("id"),
            name=raw_data.get("name"),
            description=raw_data.get("description"),
            status=raw_data.get("investigation_status"),
            severity=raw_data.get("x_fireeye_com_severity"),
            modified=convert_string_to_unix_time(raw_data.get("modified")),
            alert_type=raw_data.get("type"),
            external_id=raw_data.get("external_references")[0].get("external_id"),
            source_name=raw_data.get("external_references")[0].get("source_name"),
            events=[],
        )


@dataclasses.dataclass
class Event(BaseModel):
    """Class to create data model for Event object"""

    event_id: str
    name: str
    modified: str
    event_type: str
    note_type: str

    @classmethod
    def from_json(cls, raw_data: dict) -> Event:
        """Create Event object from raw json data

        Args:
            raw_data (dict): raw data of event

        Returns:
            Event: Event object
        """
        return cls(
            raw_data=raw_data,
            event_id=raw_data.get("id"),
            name=raw_data.get("name"),
            modified=raw_data.get("modified", ""),
            event_type=raw_data.get("type", ""),
            note_type=raw_data.get("x_fireeye_com_note_type", ""),
        )
