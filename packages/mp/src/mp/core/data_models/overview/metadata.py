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

from typing import TYPE_CHECKING, NotRequired, Self, TypedDict

import mp.core.constants
import mp.core.data_models.abc
import mp.core.utils
from mp.core.data_models.abc import RepresentableEnum

if TYPE_CHECKING:
    from pathlib import Path


class OverviewType(RepresentableEnum):
    PLAYBOOK_DEFAULT = 0
    REGULAR = 1
    SYSTEM_ALERT = 2
    SYSTEM_CASE = 3
    ALERT_TYPE = 4


class BuiltOverview(TypedDict):
    Identifier: str
    Name: str
    Creator: str | None
    PlaybookDefinitionIdentifier: str
    Type: int
    AlertRuleType: str | None
    Roles: list[int]
    RoleNames: NotRequired[list[str]]


class NonBuiltOverview(TypedDict):
    identifier: str
    name: str
    creator: str | None
    playbook_id: str
    type: str
    alert_rule_type: str | None
    roles: list[int]
    role_names: list[str]


class Overview(mp.core.data_models.abc.ComponentMetadata):
    identifier: str
    name: str
    creator: str | None
    playbook_id: str
    type_: OverviewType
    alert_rule_type: str | None
    roles: list[int]
    role_names: list[str]

    @classmethod
    def from_built_path(cls, path: Path) -> list[Self]:
        meta_path: Path = path / mp.core.constants.OVERVIEWS_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_built_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.DEF_FILE_SUFFIX}")
        ]

    @classmethod
    def from_non_built_path(cls, path: Path) -> list[Self]:
        meta_path: Path = path / mp.core.constants.OVERVIEWS_DIR
        if not meta_path.exists():
            return []

        return [
            cls._from_non_built_path(p)
            for p in meta_path.rglob(f"*{mp.core.constants.DEF_FILE_SUFFIX}")
        ]

    @classmethod
    def _from_built(cls, file_name: str, built: BuiltOverview) -> Self:
        return cls(
            identifier=built["Identifier"],
            name=built["Name"],
            creator=built["Creator"],
            playbook_id=built["PlaybookDefinitionIdentifier"],
            type_=OverviewType(built["Type"]),
            alert_rule_type=built["AlertRuleType"],
            roles=built["Roles"],
            role_names=built.get("RoleNames", []),
        )

    @classmethod
    def _from_non_built(cls, file_name: str, non_built: NonBuiltOverview) -> Self:
        return cls(
            identifier=non_built["identifier"],
            name=non_built["name"],
            creator=non_built["creator"],
            playbook_id=non_built["playbook_id"],
            type_=OverviewType.from_string(non_built["type"]),
            alert_rule_type=non_built["alert_rule_type"],
            roles=non_built["roles"],
            role_names=non_built.get("role_names", []),
        )

    def to_built(self) -> BuiltOverview:
        return BuiltOverview(
            Identifier=self.identifier,
            Name=self.name,
            Creator=self.creator,
            PlaybookDefinitionIdentifier=self.playbook_id,
            Type=self.type_.value,
            AlertRuleType=self.alert_rule_type,
            Roles=self.roles,
        )

    def to_non_built(self) -> NonBuiltOverview:
        non_built: NonBuiltOverview = NonBuiltOverview(
            identifier=self.identifier,
            name=self.name,
            creator=self.creator,
            playbook_id=self.playbook_id,
            type=self.type_.to_string(),
            alert_rule_type=self.alert_rule_type,
            roles=self.roles,
            role_names=self.role_names,
        )
        mp.core.utils.remove_none_entries_from_mapping(non_built)
        return non_built
