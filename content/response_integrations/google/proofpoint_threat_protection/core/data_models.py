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

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self

    from TIPCommon.types import SingleJson


@dataclass(slots=True)
class IntegrationParameters:
    api_root: str
    client_id: str
    client_secret: str
    verify_ssl: bool
    cluster_id: str


@dataclass(frozen=True, slots=True)
class Entry:
    raw_data: SingleJson
    attribute: str
    operator: str
    value: str
    comment: str | None

    @classmethod
    def from_json(cls, data: SingleJson) -> Self:
        return cls(
            raw_data=data,
            attribute=data.get("attribute", ""),
            operator=data.get("operator", ""),
            value=data.get("value", ""),
            comment=data.get("comment"),
        )

    def to_json(self) -> SingleJson:
        return self.raw_data


@dataclass(frozen=True, slots=True)
class AllowEntry(Entry):
    """Represents an allow list entry."""


@dataclass(frozen=True, slots=True)
class BlockEntry(Entry):
    """Represents an block list entry."""
